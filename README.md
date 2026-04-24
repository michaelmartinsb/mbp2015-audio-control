# mbp2015-audio-control

Switch the active EasyEffects playback and microphone profiles on a 2015
MacBook Pro running Linux.

The 2015 MacBook Pro routes its built-in speakers and 3.5 mm headphone jack
through a single analog device on the Cirrus Logic CS4208 codec. Linux does
not always notice when headphones are plugged in, and an EQ tuned for the
speakers can sound wrong — or clip — on headphones. This app loads the right
EasyEffects preset, and for the microphone it also makes sure input
processing is on or off as the chosen preset expects.

## Compatibility

Tested on a 2015 MacBook Pro (`MacBookPro12,1`) running Ubuntu 24.04 with
EasyEffects. The bundled presets are tuned for that exact analog path. The
app will launch on other hardware; the presets will not be meaningful there.

To verify your machine:

```bash
cat /sys/class/dmi/id/product_name
grep -i codec /proc/asound/card*/codec* 2>/dev/null | head -1
```

You should see `MacBookPro12,1` (or `11,4` / `11,5`) and `Cirrus Logic CS4208`.

## Install

```bash
git clone https://github.com/michaelmartinsb/mbp2015-audio-control.git
cd mbp2015-audio-control
./install.sh
```

The installer adds the apt packages it needs (EasyEffects, Python, the Qt
X11 libraries, `libnotify`), creates a `.venv`, installs PySide6, copies the
presets into `~/.config/easyeffects/`, and offers to add a launcher to your
application menu. It is idempotent.

### Step by step, without the script

```bash
sudo apt install easyeffects python3 python3-venv python3-pip \
    libxcb-cursor0 libxkbcommon-x11-0 libnotify-bin

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

mkdir -p ~/.config/easyeffects/input ~/.config/easyeffects/output
cp presets/input/*.json  ~/.config/easyeffects/input/
cp presets/output/*.json ~/.config/easyeffects/output/
```

For the application-menu launcher:

```bash
mkdir -p ~/.local/share/applications
sed "s|__INSTALL_DIR__|$PWD|g" \
    audio-profile-switcher.desktop.template \
    > ~/.local/share/applications/mbp2015-audio-control.desktop
chmod +x ~/.local/share/applications/mbp2015-audio-control.desktop
```

## Use

```bash
./select-audio-profile.sh
```

Or open **Audio Profile Switcher** from the application menu.

To apply a profile without opening the window:

```bash
./select-audio-profile.sh --apply-output MacBook-Speakers
./select-audio-profile.sh --apply-output Apple-EarPods
./select-audio-profile.sh --apply-input  Built-in-Mic-Default
./select-audio-profile.sh --apply-input  Built-in-Mic-Voice
./select-audio-profile.sh --apply-input  Built-in-Mic-S-Control
./select-audio-profile.sh --apply-input  Built-in-Mic-Singing
```

## Profiles

Playback (`presets/output/`):

| Profile            | For                                       |
| ------------------ | ----------------------------------------- |
| `MacBook-Speakers` | The laptop's built-in speakers            |
| `Apple-EarPods`    | Apple EarPods on the 3.5 mm jack          |

Microphone (`presets/input/`):

| Profile                  | Character                                    |
| ------------------------ | -------------------------------------------- |
| `Built-in-Mic-Default`   | Input processing off                         |
| `Built-in-Mic-Voice`     | Light cleanup; natural voice                 |
| `Built-in-Mic-S-Control` | Stronger sibilance and noise control         |
| `Built-in-Mic-Singing`   | Preserves tone, breath, and sustained tails  |

## Verifying

The active preset name appears in the EasyEffects title bar, and a desktop
notification confirms the change. From a terminal:

```bash
gsettings get com.github.wwmm.easyeffects last-used-output-preset
gsettings get com.github.wwmm.easyeffects last-used-input-preset
gsettings get com.github.wwmm.easyeffects process-all-inputs
```

`process-all-inputs` is `true` for every microphone profile other than
`Built-in-Mic-Default`.

## Troubleshooting

**`qt.qpa.plugin: Could not load the Qt platform plugin "xcb"`**
Install the Qt X11 dependencies:

```bash
sudo apt install libxcb-cursor0 libxkbcommon-x11-0
```

**"EasyEffects did not report the requested profile"**
EasyEffects needs to be running. Start it once and leave it as a background
service:

```bash
easyeffects --gapplication-service &
```

The app retries briefly to give EasyEffects a moment to apply the preset.

**The mic profile changes but nothing sounds different**
Confirm input processing is on:

```bash
gsettings get com.github.wwmm.easyeffects process-all-inputs
```

It should be `true` for every microphone profile except
`Built-in-Mic-Default`.

**The Apple EarPods microphone does not appear as an input**
A known limitation of the Linux audio stack on this hardware. Use the
built-in microphone.

**The application-menu launcher does nothing**
The `.desktop` file holds an absolute path. If the project moved, re-run
`./install.sh` or repeat the `sed` step under *Step by step*.

## Layout

```
.
├── audio-profile-switcher.py               # PySide6 GUI + CLI
├── select-audio-profile.sh                 # Launcher; finds .venv automatically
├── install.sh                              # From-zero installer
├── requirements.txt                        # PySide6
├── audio-profile-switcher.desktop.template # App-menu launcher template
├── presets/
│   ├── input/                              # Microphone EasyEffects presets
│   └── output/                             # Playback EasyEffects presets
├── LICENSE
└── README.md
```

## Uninstall

```bash
rm -f ~/.local/share/applications/mbp2015-audio-control.desktop
rm -rf .venv
rm -f ~/.config/easyeffects/output/MacBook-Speakers.json \
      ~/.config/easyeffects/output/Apple-EarPods.json \
      ~/.config/easyeffects/input/Built-in-Mic-*.json
```

Then delete the project directory. EasyEffects itself can be removed with
`sudo apt remove easyeffects`.

## License

MIT — see [LICENSE](LICENSE).
