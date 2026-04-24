#!/usr/bin/env python3
"""Qt-based control center for EasyEffects playback and microphone presets."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStyle,
    QVBoxLayout,
    QWidget,
)

# ─────────────────────────────────────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────────────────────────────────────

APP_NAME = "Audio Profile Switcher"
SCHEMA = "com.github.wwmm.easyeffects"
DEFAULT_INPUT_PROFILE = "Built-in-Mic-Default"
STATE_SETTLE_TIMEOUT_S = 2.0
STATE_SETTLE_POLL_INTERVAL_S = 0.1


# ─────────────────────────────────────────────────────────────────────────────
#  Profile metadata
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProfileSpec:
    accent: str          # "orange" | "blue" | "green"
    label: str           # Display name on the card and in summary tiles
    description: str     # Sentence describing what the profile does
    button: str          # Idle button text
    guidance: str        # Secondary "use this when…" hint


OUTPUT_PROFILES: dict[str, ProfileSpec] = {
    "MacBook-Speakers": ProfileSpec(
        accent="orange",
        label="MacBook Speakers",
        description="Use the built-in MacBook speakers.",
        button="Use MacBook Speakers",
        guidance="Best when the laptop is playing through its own built-in speakers.",
    ),
    "Apple-EarPods": ProfileSpec(
        accent="blue",
        label="Apple EarPods",
        description="Use Apple EarPods or other simple 3.5 mm headphones.",
        button="Use Apple EarPods",
        guidance="Best when 3.5 mm EarPods or headphones are plugged into the jack.",
    ),
}


INPUT_PROFILES: dict[str, ProfileSpec] = {
    DEFAULT_INPUT_PROFILE: ProfileSpec(
        accent="green",
        label="Mic Default / Rollback",
        description="Return the microphone to the current default behavior with EasyEffects input processing off.",
        button="Use Mic Default",
        guidance="Use this for rollback, baseline comparison, or the simplest recording path.",
    ),
    "Built-in-Mic-Voice": ProfileSpec(
        accent="orange",
        label="Mic Voice",
        description="The main voice baseline with stronger de-essing, a softer top end, and tighter cleanup between phrases.",
        button="Use Mic Voice",
        guidance="Use this as the main default for speech and general voice work.",
    ),
    "Built-in-Mic-S-Control": ProfileSpec(
        accent="blue",
        label="Mic S-Control",
        description="An extra-strong voice mode with heavier sibilance control, stronger pause cleanup, and less denoiser hiss between phrases.",
        button="Use Mic S-Control",
        guidance="Use this when Mic Voice still leaves S sounds too sharp or room noise too obvious; it is the more processed option with harder silent-floor cleanup.",
    ),
    "Built-in-Mic-Singing": ProfileSpec(
        accent="green",
        label="Mic Singing",
        description="A more natural singing mode with no dedicated denoiser, no hard speech-style gate, controlled S protection, and lighter peak handling.",
        button="Use Mic Singing",
        guidance="Use this for sung takes that will be edited or enhanced later; it preserves more tone, breath, and note tails than S-Control.",
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
#  Visual palette
# ─────────────────────────────────────────────────────────────────────────────
#
# Apple-leaning visual language: near-white background, white card surfaces,
# hairline borders, soft drop shadows, and Inter (SF Pro substitute) for type.
# Anthropic accents are preserved verbatim — only the neutrals and structural
# treatments change.

# Core neutrals
INK = "#1d1d1f"           # Primary text — Apple-like "label"
INK_SOFT = "#2c2c2e"
INK_DEEP = "#000000"
PARCHMENT = "#faf9f5"     # Cream — used as on-accent text on the green tone
SURFACE = "#ffffff"       # Card surface
CANVAS = "#f5f5f3"        # Window background — warm near-white
TINT_SOFT = "#fafaf8"     # Subtly raised tint (summary chips, secondary buttons)
LINE = "#e3e1d9"          # Hairline border (warm)
LINE_SOFT = "#ecebe5"
LINE_HOVER = "#d4d2ca"
TEXT_BODY = "#3a3938"
TEXT_MUTED = "#6e6c66"
TEXT_HINT = "#86857f"

# Per-accent palette — Anthropic accents preserved verbatim.
ACCENTS: dict[str, dict[str, str]] = {
    "orange": {
        "base": "#d97757", "hover": "#cc6e50", "border": "#cf6d4d",
        "tint": "#fdf4ef", "tint_hover": "#fceee5",
        "on_accent": INK,
    },
    "blue": {
        "base": "#6a9bcc", "hover": "#5d8fbe", "border": "#5f90c0",
        "tint": "#f1f6fc", "tint_hover": "#e7f0f9",
        "on_accent": INK,
    },
    "green": {
        "base": "#788c5d", "hover": "#6d8054", "border": "#6d8054",
        "tint": "#f1f6ea", "tint_hover": "#e8f0dd",
        "on_accent": PARCHMENT,
    },
}

# Font stacks — Inter installed via fonts-inter; SF Pro / system fallbacks
# preserve macOS look on non-Linux too.
FONT_STACK = (
    '"Inter", "SF Pro Text", -apple-system, '
    '"Helvetica Neue", "Segoe UI", Arial, sans-serif'
)
FONT_STACK_DISPLAY = (
    '"Inter Display", "Inter", "SF Pro Display", -apple-system, '
    '"Helvetica Neue", "Segoe UI", Arial, sans-serif'
)


def _build_stylesheet() -> str:
    """Compose the application QSS from the neutral base + per-accent rules.

    The per-accent rules are templated from ACCENTS, so adding a new accent
    only requires a new entry in that map.
    """
    base = f"""
/* ── Foundations ─────────────────────────────────────── */
QMainWindow, QWidget#canvas {{
    background-color: {CANVAS};
    color: {INK};
}}

QScrollArea {{
    border: none;
    background: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 11px;
    margin: 6px 3px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {LINE_HOVER};
    border-radius: 4px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: {TEXT_HINT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0; width: 0; background: transparent; border: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

/* ── Cards ───────────────────────────────────────────── */
QFrame#heroCard,
QFrame#sectionCard {{
    background-color: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 18px;
}}

QFrame#footerCard {{
    background-color: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 14px;
}}

QFrame#summaryCard {{
    background-color: {TINT_SOFT};
    border: 1px solid {LINE_SOFT};
    border-radius: 12px;
}}

QFrame#profileCard {{
    background-color: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 16px;
}}

QFrame#profileCard:hover {{
    border-color: {LINE_HOVER};
}}

/* ── Typography (Inter / SF feel) ────────────────────── */
QLabel#titleLabel {{
    color: {INK};
    font-family: {FONT_STACK_DISPLAY};
    font-size: 26px;
    font-weight: 600;
    letter-spacing: -0.4px;
}}

QLabel#subtitleLabel {{
    color: {TEXT_MUTED};
    font-family: {FONT_STACK};
    font-size: 13px;
    font-weight: 400;
}}

QLabel#summaryTitle {{
    color: {TEXT_HINT};
    font-family: {FONT_STACK};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.6px;
}}

QLabel#summaryValue {{
    color: {INK};
    font-family: {FONT_STACK_DISPLAY};
    font-size: 14px;
    font-weight: 600;
    letter-spacing: -0.1px;
}}

QLabel#sectionLabel {{
    color: {INK};
    font-family: {FONT_STACK_DISPLAY};
    font-size: 17px;
    font-weight: 600;
    letter-spacing: -0.2px;
}}

QLabel#sectionBody {{
    color: {TEXT_MUTED};
    font-family: {FONT_STACK};
    font-size: 13px;
    font-weight: 400;
}}

QLabel#cardTitle {{
    color: {INK};
    font-family: {FONT_STACK_DISPLAY};
    font-size: 15px;
    font-weight: 600;
    letter-spacing: -0.1px;
}}

QLabel#cardDescription {{
    color: {TEXT_BODY};
    font-family: {FONT_STACK};
    font-size: 12.5px;
    font-weight: 400;
}}

QLabel#cardGuidance {{
    color: {TEXT_MUTED};
    font-family: {FONT_STACK};
    font-size: 11.5px;
    font-weight: 400;
}}

QLabel#badgeLabel {{
    font-family: {FONT_STACK};
    font-size: 9.5px;
    font-weight: 600;
    border-radius: 999px;
    padding: 3px 10px;
    letter-spacing: 0.4px;
}}

/* ── Status banner ───────────────────────────────────── */
QLabel#statusMessage {{
    font-family: {FONT_STACK};
    padding: 10px 14px;
    border-radius: 10px;
    font-size: 12.5px;
    font-weight: 400;
}}

QLabel#statusMessage[tone="info"] {{
    background-color: {TINT_SOFT};
    color: {TEXT_BODY};
    border: 1px solid {LINE_SOFT};
}}

QLabel#statusMessage[tone="success"] {{
    background-color: #f1f6e6;
    color: #34452a;
    border: 1px solid #c2cfa6;
}}

QLabel#statusMessage[tone="error"] {{
    background-color: #fdf0e9;
    color: #5b2a1a;
    border: 1px solid #ecb39a;
}}

/* ── Buttons ─────────────────────────────────────────── */
QPushButton {{
    font-family: {FONT_STACK};
    border-radius: 9px;
    padding: 8px 18px;
    font-size: 12.5px;
    font-weight: 500;
    min-height: 32px;
}}

QPushButton#primaryButton {{
    background-color: {INK};
    color: #ffffff;
    border: 1px solid {INK};
}}

QPushButton#primaryButton:hover {{
    background-color: {INK_SOFT};
    border-color: {INK_SOFT};
}}

QPushButton#primaryButton:pressed {{
    background-color: {INK_DEEP};
}}

QPushButton#secondaryButton {{
    background-color: {TINT_SOFT};
    color: {INK};
    border: 1px solid {LINE};
}}

QPushButton#secondaryButton:hover {{
    background-color: {SURFACE};
    border-color: {LINE_HOVER};
}}

QPushButton#secondaryButton:pressed {{
    background-color: {CANVAS};
}}
"""

    accent_rules = []
    for tone, c in ACCENTS.items():
        accent_rules.append(f"""
/* ── Accent: {tone} ───────────────────────────────────── */
QFrame#profileCard[accent="{tone}"][active="true"] {{
    background-color: {c["tint"]};
    border: 1px solid {c["base"]};
}}

QFrame#profileCard[accent="{tone}"][active="true"]:hover {{
    background-color: {c["tint_hover"]};
}}

QLabel#badgeLabel[tone="{tone}"] {{
    background-color: {c["base"]};
    color: {c["on_accent"]};
    border: 1px solid {c["border"]};
}}

QPushButton#primaryButton[state="active"][tone="{tone}"] {{
    background-color: {c["base"]};
    border-color: {c["base"]};
    color: {c["on_accent"]};
}}

QPushButton#primaryButton[state="active"][tone="{tone}"]:hover {{
    background-color: {c["hover"]};
    border-color: {c["hover"]};
}}
""")

    return base + "".join(accent_rules)


APP_STYLESHEET = _build_stylesheet()


# ─────────────────────────────────────────────────────────────────────────────
#  Subprocess helpers
# ─────────────────────────────────────────────────────────────────────────────


class AudioProfileError(RuntimeError):
    pass


def run_command(args: list[str]) -> str:
    """Run a command, capture output, raise AudioProfileError on failure."""
    try:
        completed = subprocess.run(args, check=True, text=True, capture_output=True)
    except FileNotFoundError as exc:
        raise AudioProfileError(f"Missing required command: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or "Command failed."
        raise AudioProfileError(message) from exc

    return completed.stdout.strip()


def notify(summary: str, body: str, critical: bool = False) -> None:
    args = ["notify-send"]
    if critical:
        args.extend(["-u", "critical"])
    args.extend([summary, body])

    try:
        subprocess.run(args, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  EasyEffects state I/O
# ─────────────────────────────────────────────────────────────────────────────


def read_setting(key: str) -> str:
    raw = run_command(["gsettings", "get", SCHEMA, key])
    return raw.removeprefix("'").removesuffix("'")


def read_current_output_preset() -> str:
    return read_setting("last-used-output-preset")


def read_current_input_preset() -> str:
    return read_setting("last-used-input-preset")


def read_input_processing_enabled() -> bool:
    return read_setting("process-all-inputs") == "true"


def wait_for_reported_value(
    reader: Callable[[], str | bool],
    expected: str | bool,
    *,
    timeout_s: float = STATE_SETTLE_TIMEOUT_S,
    poll_interval_s: float = STATE_SETTLE_POLL_INTERVAL_S,
) -> str | bool:
    """Poll a reported EasyEffects value until it matches or timeout expires."""
    deadline = time.monotonic() + timeout_s
    last_seen = reader()

    while last_seen != expected and time.monotonic() < deadline:
        time.sleep(poll_interval_s)
        last_seen = reader()

    return last_seen


# pactl "Active Port:" name → human-friendly summary
_OUTPUT_PORT_NAMES: dict[str, str] = {
    "analog-output-headphones": "Headphones jack is active",
    "analog-output-speaker": "Built-in speakers are active",
}

_INPUT_PORT_NAMES: dict[str, str] = {
    "analog-input-internal-mic": "Built-in microphone is active",
    "analog-input-mic": "External analog mic is active",
}


def _read_active_port(pactl_kind: str, port_names: dict[str, str]) -> str:
    """Return a human label for the first 'Active Port:' line in pactl output.

    Unknown ports are returned verbatim; any failure falls back to "Unknown".
    """
    try:
        output = run_command(["pactl", "list", pactl_kind])
    except AudioProfileError:
        return "Unknown"

    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Active Port:"):
            port = stripped.split(":", 1)[1].strip()
            return port_names.get(port, port)

    return "Unknown"


def read_active_output_port() -> str:
    return _read_active_port("sinks", _OUTPUT_PORT_NAMES)


def read_active_input_port() -> str:
    return _read_active_port("sources", _INPUT_PORT_NAMES)


def ensure_service_running() -> None:
    running = subprocess.run(
        ["pgrep", "-x", "easyeffects"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if running.returncode == 0:
        return

    try:
        subprocess.Popen(
            ["easyeffects", "--gapplication-service"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except FileNotFoundError as exc:
        raise AudioProfileError("Missing required command: easyeffects") from exc

    time.sleep(2)


# ─────────────────────────────────────────────────────────────────────────────
#  Profile application
# ─────────────────────────────────────────────────────────────────────────────


def apply_output_profile(profile: str) -> str:
    if profile not in OUTPUT_PROFILES:
        raise AudioProfileError(f"Unknown playback profile: {profile}")

    ensure_service_running()
    run_command(["easyeffects", "-l", profile])
    active = wait_for_reported_value(read_current_output_preset, profile)

    if active != profile:
        raise AudioProfileError(
            "EasyEffects did not report the requested playback profile as active."
        )

    notify(APP_NAME, f"Active playback profile: {OUTPUT_PROFILES[active].label}")
    return active


def apply_input_profile(profile: str) -> str:
    if profile not in INPUT_PROFILES:
        raise AudioProfileError(f"Unknown microphone profile: {profile}")

    ensure_service_running()

    # The "Default / Rollback" preset means: select it, but disable input
    # processing entirely. All other presets enable processing.
    should_process = profile != DEFAULT_INPUT_PROFILE
    run_command(["gsettings", "set", SCHEMA, "last-used-input-preset", profile])
    run_command(
        ["gsettings", "set", SCHEMA, "process-all-inputs",
         "true" if should_process else "false"]
    )

    active = wait_for_reported_value(read_current_input_preset, profile)
    enabled = wait_for_reported_value(read_input_processing_enabled, should_process)

    if active != profile:
        raise AudioProfileError(
            "EasyEffects did not report the requested microphone profile as active."
        )
    if not should_process and enabled:
        raise AudioProfileError(
            "EasyEffects input processing stayed enabled when the default microphone mode was requested."
        )
    if should_process and not enabled:
        raise AudioProfileError(
            "EasyEffects input processing did not turn on for the selected microphone profile."
        )

    notify(APP_NAME, f"Active microphone profile: {INPUT_PROFILES[active].label}")
    return active


# ─────────────────────────────────────────────────────────────────────────────
#  Qt helpers
# ─────────────────────────────────────────────────────────────────────────────


def repolish(widget: QWidget) -> None:
    """Force CSS re-evaluation after a setProperty change."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def apply_card_shadow(
    widget: QWidget, *, blur: int = 22, y: int = 3, alpha: int = 22
) -> None:
    """Attach a soft, macOS-style drop shadow to a card.

    Defaults are tuned to be barely-visible at rest (Apple-style "lift") but
    enough to give surfaces a sense of layering above the canvas.
    """
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)


def configure_application(app: QApplication) -> None:
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")

    # Inter (with SF / system fallbacks) for menus, dialogs, native chrome.
    base_font = QFont("Inter", 10)
    base_font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(base_font)

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(CANVAS))
    palette.setColor(QPalette.WindowText, QColor(INK))
    palette.setColor(QPalette.Base, QColor(SURFACE))
    palette.setColor(QPalette.AlternateBase, QColor(TINT_SOFT))
    palette.setColor(QPalette.ToolTipBase, QColor(INK))
    palette.setColor(QPalette.ToolTipText, QColor(PARCHMENT))
    palette.setColor(QPalette.Text, QColor(INK))
    palette.setColor(QPalette.Button, QColor(SURFACE))
    palette.setColor(QPalette.ButtonText, QColor(INK))
    palette.setColor(QPalette.BrightText, QColor(PARCHMENT))
    palette.setColor(QPalette.Link, QColor(ACCENTS["blue"]["base"]))
    palette.setColor(QPalette.Highlight, QColor(ACCENTS["blue"]["base"]))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)
    app.setStyleSheet(APP_STYLESHEET)


# ─────────────────────────────────────────────────────────────────────────────
#  UI widgets
# ─────────────────────────────────────────────────────────────────────────────


class ProfileCard(QFrame):
    """A single profile card: title with optional active badge, copy, action button."""

    def __init__(
        self,
        profile: str,
        spec: ProfileSpec,
        callback: Callable[[str], None],
    ) -> None:
        super().__init__()
        self.profile = profile
        self._spec = spec

        self.setObjectName("profileCard")
        self.setAttribute(Qt.WA_Hover, True)
        self.setProperty("accent", spec.accent)
        self.setProperty("active", "false")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)

        # Header: title (left) + active badge (right). Apple-selection pattern.
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)

        title = QLabel(spec.label)
        title.setObjectName("cardTitle")
        header.addWidget(title)
        header.addStretch(1)

        self.badge = QLabel("ACTIVE")
        self.badge.setObjectName("badgeLabel")
        self.badge.setProperty("tone", spec.accent)
        self.badge.setVisible(False)
        header.addWidget(self.badge, 0, Qt.AlignTop | Qt.AlignRight)

        layout.addLayout(header)

        description = QLabel(spec.description)
        description.setObjectName("cardDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        guidance = QLabel(spec.guidance)
        guidance.setObjectName("cardGuidance")
        guidance.setWordWrap(True)
        layout.addWidget(guidance)

        layout.addStretch(1)

        self.button = QPushButton(spec.button)
        self.button.setObjectName("primaryButton")
        self.button.setProperty("tone", spec.accent)
        self.button.setProperty("state", "idle")
        self.button.setCursor(QCursor(Qt.PointingHandCursor))
        self.button.clicked.connect(lambda: callback(profile))
        layout.addWidget(self.button)

        apply_card_shadow(self, blur=18, y=2, alpha=16)

    def set_active(self, active: bool) -> None:
        self.setProperty("active", "true" if active else "false")
        repolish(self)

        self.badge.setVisible(active)
        repolish(self.badge)

        if active:
            self.button.setText(f"✓  {self._spec.label}")
            self.button.setProperty("state", "active")
        else:
            self.button.setText(self._spec.button)
            self.button.setProperty("state", "idle")
        repolish(self.button)


class AudioProfileWindow(QMainWindow):
    """Main window — hero summary + playback section + microphone section."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 860)
        self.setMinimumSize(1020, 720)
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_MediaVolume))

        self.output_cards: dict[str, ProfileCard] = {}
        self.input_cards: dict[str, ProfileCard] = {}
        self.summary_labels: dict[str, QLabel] = {}

        self._build_ui()
        self.refresh_state()

    # ── Layout construction ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        root.addWidget(scroll)

        canvas = QWidget()
        canvas.setObjectName("canvas")
        scroll.setWidget(canvas)

        outer = QVBoxLayout(canvas)
        outer.setContentsMargins(28, 28, 28, 28)
        outer.setSpacing(20)

        outer.addWidget(self._build_hero_card())
        outer.addWidget(self._build_section(
            title="Playback",
            description="Choose the output profile that matches the hardware currently in use.",
            profiles=OUTPUT_PROFILES,
            store=self.output_cards,
            callback=self.on_apply_output,
        ))
        outer.addWidget(self._build_section(
            title="Microphone",
            description="Switch between rollback, balanced voice, stronger S-control, and singing-oriented capture modes.",
            profiles=INPUT_PROFILES,
            store=self.input_cards,
            callback=self.on_apply_input,
        ))
        outer.addWidget(self._build_footer_card())
        outer.addStretch(1)

        self.setCentralWidget(central)

    def _build_hero_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("heroCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        title_block = QVBoxLayout()
        title_block.setSpacing(6)

        title = QLabel("Audio Profile Switcher")
        title.setObjectName("titleLabel")
        title_block.addWidget(title)

        subtitle = QLabel(
            "Control center for EasyEffects playback and microphone presets on this MacBook."
        )
        subtitle.setObjectName("subtitleLabel")
        subtitle.setWordWrap(True)
        title_block.addWidget(subtitle)

        layout.addLayout(title_block)

        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(12)
        summary_grid.setVerticalSpacing(12)

        summary_specs = (
            ("current_output", "Current playback profile"),
            ("output_port", "Current hardware output"),
            ("current_input", "Current microphone profile"),
            ("input_port", "Current hardware input"),
        )
        for index, (key, label_text) in enumerate(summary_specs):
            tile, value_label = self._build_summary_tile(label_text)
            row, column = divmod(index, 2)
            summary_grid.addWidget(tile, row, column)
            self.summary_labels[key] = value_label

        layout.addLayout(summary_grid)
        apply_card_shadow(card, blur=30, y=4, alpha=22)
        return card

    def _build_summary_tile(self, title: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setObjectName("summaryCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(6)

        # Pre-uppercased — Qt QSS does not support text-transform.
        title_label = QLabel(title.upper())
        title_label.setObjectName("summaryTitle")
        layout.addWidget(title_label)

        value_label = QLabel("Loading…")
        value_label.setObjectName("summaryValue")
        value_label.setWordWrap(True)
        layout.addWidget(value_label)

        return card, value_label

    def _build_section(
        self,
        *,
        title: str,
        description: str,
        profiles: dict[str, ProfileSpec],
        store: dict[str, ProfileCard],
        callback: Callable[[str], None],
    ) -> QFrame:
        section = QFrame()
        section.setObjectName("sectionCard")

        layout = QVBoxLayout(section)
        layout.setContentsMargins(28, 26, 28, 28)
        layout.setSpacing(18)

        title_label = QLabel(title)
        title_label.setObjectName("sectionLabel")
        layout.addWidget(title_label)

        description_label = QLabel(description)
        description_label.setObjectName("sectionBody")
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        columns = 2

        for index, (profile, spec) in enumerate(profiles.items()):
            row, column = divmod(index, columns)
            card = ProfileCard(profile, spec, callback)
            grid.addWidget(card, row, column)
            store[profile] = card

        layout.addLayout(grid)
        apply_card_shadow(section, blur=26, y=3, alpha=18)
        return section

    def _build_footer_card(self) -> QFrame:
        footer = QFrame()
        footer.setObjectName("footerCard")

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        self.status_message = QLabel(
            "Ready. Use playback for speakers or EarPods, and microphone modes for rollback, voice, S-control, or singing capture."
        )
        self.status_message.setObjectName("statusMessage")
        self.status_message.setWordWrap(True)
        self.status_message.setProperty("tone", "info")
        repolish(self.status_message)
        layout.addWidget(self.status_message, 1)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        button_row.addWidget(self._build_secondary_button(
            "Refresh", QStyle.SP_BrowserReload, self.refresh_state
        ))
        button_row.addWidget(self._build_secondary_button(
            "Close", QStyle.SP_DialogCloseButton, self.close
        ))
        layout.addLayout(button_row)

        apply_card_shadow(footer, blur=20, y=2, alpha=14)
        return footer

    def _build_secondary_button(
        self, text: str, icon: QStyle.StandardPixmap, callback: Callable[[], None]
    ) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("secondaryButton")
        button.setIcon(self.style().standardIcon(icon))
        button.setCursor(QCursor(Qt.PointingHandCursor))
        button.clicked.connect(callback)
        return button

    # ── State sync ──────────────────────────────────────────────────────────

    def _set_status_message(self, text: str, tone: str) -> None:
        self.status_message.setText(text)
        self.status_message.setProperty("tone", tone)
        repolish(self.status_message)

    def refresh_state(self) -> None:
        active_output = read_current_output_preset()
        active_input = read_current_input_preset()
        input_enabled = read_input_processing_enabled()

        output_spec = OUTPUT_PROFILES.get(active_output)
        output_label = output_spec.label if output_spec else (active_output or "Unknown")

        if input_enabled:
            input_spec = INPUT_PROFILES.get(active_input)
            input_label = input_spec.label if input_spec else (active_input or "Unknown")
            input_summary = f"{input_label} (EasyEffects input on)"
        else:
            input_summary = "Mic Default / Rollback (EasyEffects input off)"

        self.summary_labels["current_output"].setText(output_label)
        self.summary_labels["output_port"].setText(read_active_output_port())
        self.summary_labels["current_input"].setText(input_summary)
        self.summary_labels["input_port"].setText(read_active_input_port())

        for profile, card in self.output_cards.items():
            card.set_active(profile == active_output)

        for profile, card in self.input_cards.items():
            is_default = profile == DEFAULT_INPUT_PROFILE
            is_active = (
                (is_default and not input_enabled)
                or (profile == active_input and input_enabled)
            )
            card.set_active(is_active)

    # ── Apply actions ───────────────────────────────────────────────────────

    def _apply_profile(
        self,
        *,
        profile: str,
        apply_func: Callable[[str], str],
        profile_map: dict[str, ProfileSpec],
        category_name: str,
    ) -> None:
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            active = apply_func(profile)
        except AudioProfileError as exc:
            notify(APP_NAME, str(exc), critical=True)
            self._set_status_message(str(exc), "error")
            QMessageBox.critical(self, APP_NAME, str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()

        self.refresh_state()
        self._set_status_message(
            f"Switched {category_name} successfully. Active profile: {profile_map[active].label}",
            "success",
        )

    def on_apply_output(self, profile: str) -> None:
        self._apply_profile(
            profile=profile,
            apply_func=apply_output_profile,
            profile_map=OUTPUT_PROFILES,
            category_name="playback",
        )

    def on_apply_input(self, profile: str) -> None:
        self._apply_profile(
            profile=profile,
            apply_func=apply_input_profile,
            profile_map=INPUT_PROFILES,
            category_name="microphone",
        )

    def run(self) -> int:
        self.showMaximized()
        return QApplication.instance().exec()


# ─────────────────────────────────────────────────────────────────────────────
#  CLI / entry point
# ─────────────────────────────────────────────────────────────────────────────


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Switch the active EasyEffects playback or microphone profile."
    )
    parser.add_argument(
        "--apply",
        choices=sorted([*OUTPUT_PROFILES, *INPUT_PROFILES]),
        help="Apply a profile directly without opening the GUI.",
    )
    parser.add_argument(
        "--apply-output",
        choices=sorted(OUTPUT_PROFILES),
        help="Apply a playback profile directly.",
    )
    parser.add_argument(
        "--apply-input",
        choices=sorted(INPUT_PROFILES),
        help="Apply a microphone profile directly.",
    )
    return parser.parse_args(argv)


def show_error_dialog(message: str) -> None:
    if QApplication.instance() is None:
        app = QApplication([APP_NAME])
        configure_application(app)
    QMessageBox.critical(None, APP_NAME, message)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    # CLI shortcut: dispatch to the right apply func based on which flag was
    # set. --apply-output / --apply-input win over the generic --apply.
    if args.apply_output:
        print(apply_output_profile(args.apply_output))
        return 0
    if args.apply_input:
        print(apply_input_profile(args.apply_input))
        return 0
    if args.apply:
        apply_func = (
            apply_output_profile if args.apply in OUTPUT_PROFILES
            else apply_input_profile
        )
        print(apply_func(args.apply))
        return 0

    if QApplication.instance() is None:
        app = QApplication([APP_NAME])
        configure_application(app)

    return AudioProfileWindow().run()


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except AudioProfileError as exc:
        notify(APP_NAME, str(exc), critical=True)
        show_error_dialog(str(exc))
        raise SystemExit(1)
