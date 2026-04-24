# mbp2015-audio-control

A small desktop app that lets a 2015 MacBook Pro running Linux switch between
**playback** profiles (built-in speakers vs. 3.5 mm headphones) and
**microphone** profiles (built-in mic tuned for voice, sibilance control, or
singing) with a single click.

It is a thin, friendly front end over [EasyEffects](https://github.com/wwmm/easyeffects)
presets. The app does not change your audio hardware drivers; it just tells
EasyEffects which preset to load and, for the microphone, whether to process
input at all.

---

## Is this for you?

This project is built and tested on **one specific machine**: a 2015 MacBook
Pro running Ubuntu 24.04 LTS with EasyEffects. The presets are tuned for the
analog output and built-in microphone of that exact hardware path.

You are most likely a good fit if **all of these** are true:

- Your laptop is a 2015 MacBook Pro
  (model identifiers `MacBookPro12,1`, `MacBookPro11,4`, or `MacBookPro11,5`)
- Your audio codec is **Cirrus Logic CS4208**
- You are running a recent Ubuntu / Xubuntu / Debian-family Linux with
  PipeWire and EasyEffects available
- You are okay manually switching between speakers and headphones, because
  the kernel driver does not auto-route reliably on this hardware

You can verify your machine in a terminal:

```bash
# Should print something like: MacBookPro12,1
cat /sys/class/dmi/id/product_name

# Should mention: Cirrus Logic CS4208
grep -i codec /proc/asound/card*/codec* 2>/dev/null | head -1
```

If your hardware is different, the **app** will still run, but the bundled
presets will not be tuned for your speakers / mic and the speaker-vs-headphone
switching may not be needed.

---

## What it does, in plain English

On the 2015 MacBook Pro, the built-in speakers and the 3.5 mm headphone jack
share **one** analog audio device through the Cirrus Logic CS4208 codec.
The Linux driver does not always notice when you plug headphones in, and
EasyEffects' speaker-tuned EQ then either sounds wrong on headphones or
clips them.

This app fixes that with two buttons:

- **Playback profile** — load the EasyEffects output preset for either
  the MacBook speakers or Apple EarPods.
- **Microphone profile** — pick a built-in-mic mode (off / voice /
  sibilance control / singing) and the app makes sure EasyEffects is
  actually processing input.

It also pops a desktop notification on success or failure so you know
the change actually took.

---

## Quick install (recommended)

```bash
git clone https://github.com/michaelmartinsb/mbp2015-audio-control.git
cd mbp2015-audio-control
./install.sh
```

`install.sh` will:

1. `apt install` EasyEffects, Python, and the Qt system libraries the GUI needs
2. Create a local Python virtual environment in `.venv/`
3. Install `PySide6` into that venv
4. Copy the bundled EasyEffects presets into `~/.config/easyeffects/`
5. Optionally install a desktop launcher into your application menu

It is safe to re-run.

---

## Manual install (if you want to know what is happening)

System packages:

```bash
sudo apt update
sudo apt install easyeffects \
    python3 python3-venv python3-pip \
    libxcb-cursor0 libxkbcommon-x11-0 libnotify-bin
```

Python environment:

```bash
cd mbp2015-audio-control
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

EasyEffects presets:

```bash
mkdir -p ~/.config/easyeffects/input ~/.config/easyeffects/output
cp presets/input/*.json  ~/.config/easyeffects/input/
cp presets/output/*.json ~/.config/easyeffects/output/
```

Optional desktop launcher (so it shows in your application menu):

```bash
mkdir -p ~/.local/share/applications
sed "s|__INSTALL_DIR__|$PWD|g" \
    audio-profile-switcher.desktop.template \
    > ~/.local/share/applications/mbp2015-audio-control.desktop
chmod +x ~/.local/share/applications/mbp2015-audio-control.desktop
```

---

## Running it

Start the GUI:

```bash
./select-audio-profile.sh
```

Or launch **Audio Profile Switcher** from your application menu (if you
installed the desktop launcher).

CLI usage (no window, useful for shortcuts):

```bash
./select-audio-profile.sh --apply-output MacBook-Speakers
./select-audio-profile.sh --apply-output Apple-EarPods
./select-audio-profile.sh --apply-input  Built-in-Mic-Default
./select-audio-profile.sh --apply-input  Built-in-Mic-Voice
./select-audio-profile.sh --apply-input  Built-in-Mic-S-Control
./select-audio-profile.sh --apply-input  Built-in-Mic-Singing
```

---

## Profiles included

**Playback (`presets/output/`)**

| Profile           | Use when                                                    |
| ----------------- | ----------------------------------------------------------- |
| `MacBook-Speakers`| Listening through the laptop's built-in speakers            |
| `Apple-EarPods`   | Listening through Apple EarPods on the 3.5 mm jack          |

**Microphone (`presets/input/`)**

| Profile                  | Character                                                |
| ------------------------ | -------------------------------------------------------- |
| `Built-in-Mic-Default`   | Baseline / off — EasyEffects input processing disabled    |
| `Built-in-Mic-Voice`     | Natural voice baseline with light cleanup                |
| `Built-in-Mic-S-Control` | Stronger sibilance & noise control; more processed sound |
| `Built-in-Mic-Singing`   | Preserves tone, breath, and sustained note tails         |

---

## Verifying it worked

After clicking a button you should see:

- A desktop notification confirming the new profile
- In **EasyEffects**, the active preset name in the top bar matches what
  you picked
- For mic profiles other than Default: EasyEffects' input section is
  enabled (the input processing toggle is on)

You can confirm from the terminal too:

```bash
gsettings get com.github.wwmm.easyeffects last-used-output-preset
gsettings get com.github.wwmm.easyeffects last-used-input-preset
gsettings get com.github.wwmm.easyeffects process-all-inputs
```

---

## Troubleshooting

**"qt.qpa.plugin: Could not load the Qt platform plugin 'xcb'"**
Install the missing X libraries:

```bash
sudo apt install libxcb-cursor0 libxkbcommon-x11-0
```

**Nothing happens when I click, or "EasyEffects did not report the requested profile"**
Make sure EasyEffects is running first:

```bash
easyeffects --gapplication-service &
```

The app will retry briefly to give EasyEffects a moment to apply the
preset. If it still fails, open EasyEffects manually once and confirm
the presets show up under *Presets → Local presets*.

**The mic profile changes but I don't hear any difference**
Check that EasyEffects input processing is on:

```bash
gsettings get com.github.wwmm.easyeffects process-all-inputs
```

Should be `true` for any profile other than `Built-in-Mic-Default`.

**Apple EarPods microphone doesn't appear as an input**
This is a known limitation of the Linux audio stack on this hardware —
the EarPods mic is not detected. Use the built-in microphone instead.
There is no workaround in this project.

**Desktop launcher icon doesn't open the app**
The `.desktop` file's `Exec=` and `Path=` need absolute paths. If you
moved the project after install, re-run `./install.sh` (it rewrites the
launcher) or run the manual `sed` step above again.

---

## Project layout

```
.
├── audio-profile-switcher.py              # PySide6 / Qt GUI + CLI
├── select-audio-profile.sh                # Launcher (finds .venv automatically)
├── install.sh                             # From-zero installer
├── requirements.txt                       # Python deps (PySide6)
├── audio-profile-switcher.desktop.template# App-menu launcher template
├── presets/
│   ├── input/                             # Microphone EasyEffects presets
│   └── output/                            # Playback EasyEffects presets
├── LICENSE                                # MIT
└── README.md
```

---

## Uninstall

```bash
# Remove the desktop launcher
rm -f ~/.local/share/applications/mbp2015-audio-control.desktop

# Remove the Python virtual environment
rm -rf .venv

# Optionally remove the bundled presets
rm -f ~/.config/easyeffects/output/MacBook-Speakers.json
rm -f ~/.config/easyeffects/output/Apple-EarPods.json
rm -f ~/.config/easyeffects/input/Built-in-Mic-*.json

# Then delete the project directory
```

EasyEffects itself can be removed with `sudo apt remove easyeffects` if
you no longer want it.

---

## License

MIT — see [LICENSE](LICENSE).
