# mbp2015-audio-control

Machine-tuned EasyEffects control center for a **2015 MacBook Pro running Linux**.

This project packages:

- a PySide6 desktop GUI for switching playback and microphone modes
- a small launcher script for running the app
- exported EasyEffects presets for the built-in speakers, 3.5 mm EarPods, and built-in microphone

## Scope

The application itself is reusable, but the included presets are tuned for this specific machine class and audio path. They are most likely to be useful on:

- a 2015 MacBook Pro
- Linux systems using EasyEffects and a similar internal speaker / headphone jack / built-in mic setup

## Project layout

```text
audio-profile-switcher.py      Main PySide6 application
select-audio-profile.sh        Launcher script
presets/
  input/                       EasyEffects microphone presets
  output/                      EasyEffects playback presets
```

## Requirements

- Linux
- EasyEffects
- Python 3
- PySide6

The launcher looks for Python in this order:

1. `./.venv/bin/python`
2. `~/venvs/audio-profile-switcher/bin/python`
3. `python3`

## Install

```bash
cd ~/projects/mbp2015-audio-control
python3 -m venv .venv
./.venv/bin/pip install PySide6
mkdir -p ~/.config/easyeffects/input ~/.config/easyeffects/output
cp presets/input/*.json ~/.config/easyeffects/input/
cp presets/output/*.json ~/.config/easyeffects/output/
```

## Run

```bash
./select-audio-profile.sh
```

## CLI shortcuts

```bash
./select-audio-profile.sh --apply-output MacBook-Speakers
./select-audio-profile.sh --apply-output Apple-EarPods
./select-audio-profile.sh --apply-input Built-in-Mic-Default
./select-audio-profile.sh --apply-input Built-in-Mic-Voice
./select-audio-profile.sh --apply-input Built-in-Mic-S-Control
./select-audio-profile.sh --apply-input Built-in-Mic-Singing
```

## Preset overview

### Output

- `MacBook-Speakers`: conservative playback tuning for the built-in speakers
- `Apple-EarPods`: conservative playback tuning for simple 3.5 mm EarPods / headphones

### Input

- `Built-in-Mic-Default`: rollback / baseline with EasyEffects input processing off
- `Built-in-Mic-Voice`: main speech baseline
- `Built-in-Mic-S-Control`: stronger sibilance control and cleanup
- `Built-in-Mic-Singing`: more natural singing-oriented capture mode

## Notes

- The built-in microphone is the intended recording path on this machine.
- The Apple EarPods microphone is not detected on the current Linux audio stack used here.
- The GUI starts maximized but remains resizable.
