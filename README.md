# Whipper GUI

A Linux GUI front-end for the [`whipper`](https://github.com/whipper-team/whipper) audio-CD ripping CLI. Aims for EAC-equivalent (Exact Audio Copy) archival quality on Linux, packaged as a single-file AppImage.

> **Status: pre-alpha.** The application is implemented end-to-end and has 280+ unit tests, but it has not yet been validated against a real CD on a real Bazzite system. See [TASKS.md](TASKS.md) — T32 (end-to-end smoke test) is the only remaining P0 task.

## At a glance

- **Linux only.** Primary target is Bazzite KDE Plasma 6; should work on any modern desktop Linux running Qt 6 (Fedora, Arch, Ubuntu, Tumbleweed).
- **Runs whipper inside Distrobox.** The GUI calls the host-exported `whipper` binary; it never bundles whipper or tries to install it. This is intentional — see [PLANNING.md §8 KDD-07](PLANNING.md).
- **Single-file AppImage** for the GUI itself; no system-level installs required.
- **Bypasses whipper's interactive prompt** by querying MusicBrainz directly and passing `--release-id` to whipper. You never see a terminal prompt.
- **Distribution model:** AppImage primary, `pipx` secondary.

---

## Installation

There are five things to set up. Plan on **20-40 minutes** the first time. Once it's done, you don't touch most of it again.

| Step | What | Why |
|------|------|-----|
| 1 | Install Distrobox | Provides an isolated Fedora environment for whipper |
| 2 | Create a `ripping` container | Where whipper actually lives |
| 3 | Install whipper + flac in the container | The tools that do the ripping |
| 4 | Export them to the host | So Whipper GUI can find them |
| 5 | Detect your drive's read offset | One-time calibration for accurate rips |
| 6 | Install MusicBrainz Picard *(optional)* | Manual tag editing for unknown discs |
| 7 | Install Whipper GUI | This project |

### Step 1 — Install Distrobox

Distrobox lets you run a different Linux distribution's tools alongside your host system. It's the recommended way to run whipper on immutable distros like Bazzite.

**On Bazzite (already pre-installed):**

```bash
distrobox --version
```

If you see a version, skip to Step 2.

**On Fedora / Fedora Silverblue:**

```bash
sudo dnf install distrobox
```

**On Arch / Manjaro:**

```bash
sudo pacman -S distrobox
```

**On Ubuntu / Debian (24.04+):**

```bash
sudo apt install distrobox
```

**On older systems:**

Distrobox has a one-line installer:

```bash
curl -s https://raw.githubusercontent.com/89luca89/distrobox/main/install | sudo sh
```

Verify with `distrobox --version`.

### Step 2 — Create the `ripping` container

Create a Fedora-based container named `ripping`. The brief specifies Fedora 40; later Fedora versions also work — substitute `:41` or `:latest` if you prefer.

```bash
distrobox create --name ripping --image registry.fedoraproject.org/fedora-toolbox:40
```

This downloads about 600 MB the first time. Once it finishes:

```bash
distrobox enter ripping
```

You're now inside the container. The prompt should change to show you're in the `ripping` environment. To leave at any time, type `exit`.

### Step 3 — Install whipper and metaflac

Inside the container (your prompt should still show you're in `ripping`):

```bash
sudo dnf install whipper flac
```

Verify both are installed:

```bash
whipper --version
metaflac --version
```

`whipper` should report `0.10.0` or newer. `metaflac` is part of the `flac` package.

**Optional but recommended** — accept the MusicBrainz user-agent prompt the first time you query MusicBrainz, so future rips don't get throttled.

### Step 4 — Export the binaries to your host

Still inside the container, export both binaries:

```bash
distrobox-export --bin /usr/bin/whipper
distrobox-export --bin /usr/bin/metaflac
```

This creates wrapper scripts at `~/.local/bin/whipper` and `~/.local/bin/metaflac` on the **host** (not in the container). Those wrappers transparently enter the container when called, so from the host's perspective whipper looks like a regular installed program.

Now leave the container:

```bash
exit
```

You're back on the host. Verify the wrappers work:

```bash
which whipper
# → /home/<you>/.local/bin/whipper

whipper --version
# → whipper 0.10.0
```

If `which` returns nothing, your `~/.local/bin` isn't on `$PATH`. Most desktop Linux setups put it there automatically; if yours doesn't, add this to `~/.bashrc` or `~/.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then open a new terminal.

### Step 5 — Detect your drive's read offset

Every optical drive reads audio slightly off from where it "should" — by a positive or negative number of samples. For bit-perfect archival rips that match AccurateRip's database, whipper needs to know your drive's offset.

**The easy way** — let whipper figure it out:

```bash
whipper drive analyze
whipper offset find
```

Both commands probe your drive and write results into `~/.config/whipper/whipper.conf` automatically. `offset find` ejects and re-ingests the disc several times, takes a few minutes, and needs a CD in the drive that's in [AccurateRip's database](https://www.accuraterip.com) (most commercial CDs are).

**The manual way** — look up your drive in the [AccurateRip offset list](https://www.accuraterip.com/driveoffsets.htm), then edit `~/.config/whipper/whipper.conf` by hand:

```ini
[drive:PIONEER :BD-RW   BDR-209D:1.51]
defeats_cache = True
read_offset = 667
```

The section header is `[drive:<vendor> :<model>:<firmware>]`. Get the exact string (including odd spacing) from `whipper drive list`:

```bash
whipper drive list
# → drive: /dev/sr0, vendor: PIONEER, model: BD-RW   BDR-209D, release: 1.51
```

The pattern is `drive:<vendor> :<model>:<release>` — note the space after the vendor name and before the colon.

`defeats_cache = True` means your drive supports the audio-cache defeat command (essential for accurate ripping). If `whipper drive analyze` couldn't confirm this for your drive, leave the line off — whipper will warn but still rip.

### Step 6 — Install MusicBrainz Picard *(optional)*

Picard is what you'll use to manually fix tags for discs MusicBrainz doesn't recognize. The GUI offers to install it automatically when you first need it, but you can pre-install if you'd rather:

```bash
flatpak install --user flathub org.musicbrainz.Picard
```

Verify:

```bash
flatpak run org.musicbrainz.Picard --version
```

Whipper GUI will auto-launch Picard with the rip folder when you mark a disc as Unknown Album, *if* you enable the toggle in Settings.

### Step 7 — Install Whipper GUI

Pick **one** of the methods below.

#### Method A — AppImage (recommended for end users)

> The AppImage is not yet published as a release artifact. Until it is, use Method B or Method C below to build one yourself or run from source.

When the AppImage is available:

```bash
chmod +x whipper-gui-x86_64.AppImage
./whipper-gui-x86_64.AppImage
```

To integrate it with KDE's application menu, drop it in `~/Applications/` and use [AppImageLauncher](https://github.com/TheAssassin/AppImageLauncher) or KDE's "Install AppImage" right-click option.

#### Method B — pipx (recommended for technical users)

`pipx` installs Python applications in isolated environments and adds them to your `PATH`.

Install pipx if you don't have it (Bazzite ships with it):

```bash
sudo dnf install pipx     # Fedora / Bazzite
# or
sudo apt install pipx     # Ubuntu / Debian
```

Then install Whipper GUI:

```bash
pipx install whipper-gui
```

> The wheel is not yet published to PyPI. Until it is, install from a local checkout: `git clone …` then `pipx install .` from inside the repo.

Run with `whipper-gui` from any terminal.

#### Method C — From source (for developers / current state)

```bash
git clone https://github.com/rmccann-hub/Whipper-GUI-Frontend---CD-Rip.git
cd Whipper-GUI-Frontend---CD-Rip
pip install -e .
whipper-gui
```

To build an AppImage from your local checkout:

```bash
pip install --user build "python-appimage>=1.4,<2"
bash build/build_appimage.sh
```

The resulting `whipper-gui-x86_64.AppImage` appears at the repo root. See [`build/python-appimage/README.md`](build/python-appimage/README.md) for details.

---

## First run

When you launch Whipper GUI for the first time:

1. **Dependency check.** The GUI verifies whipper, metaflac, and Picard are reachable. If anything's missing, it pops a dialog with one of three resolutions:
   - **Auto-install** (Picard): one OK and it runs `flatpak install --user`.
   - **Pending installs:** a checklist for items that need batching or confirmation.
   - **Manual install:** a copyable search string for items like `libdiscid` that need root + reboot.

2. **Pick a drive.** The dropdown at the top of the window lists everything `whipper drive list` returns. Click Refresh if you plug in a drive after launch.

3. **Insert a CD.** The GUI fetches the disc's MusicBrainz ID, looks it up, and shows the match status. If multiple releases match, a picker dialog appears (this is the GUI's substitute for whipper's interactive TTY prompt — you'll never see whipper itself ask you anything).

4. **Edit metadata.** The track table is editable. Fix any tags that look wrong before you rip.

5. **Click "Start rip."** Progress and per-track AccurateRip confidence appear as the rip runs. You can cancel mid-rip.

6. **View the log.** When the rip finishes, the "View log" button opens the rip log in your default text editor.

For discs MusicBrainz doesn't recognize, use the Unknown Album flow from the menu — the GUI rips with placeholder `Track NN` tags and optionally launches Picard for you to fix them up.

---

## Troubleshooting

### `whipper: command not found`

Your `~/.local/bin` isn't on `$PATH`. Add this to `~/.bashrc` or `~/.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Open a new terminal. Verify with `which whipper`.

### "no drives found" when launching the GUI

The Distrobox container can't see `/dev/sr0`. Bazzite, Fedora Silverblue, and most modern distros pass optical drives through automatically. If yours doesn't:

```bash
distrobox stop ripping
distrobox enter ripping
# inside the container:
sudo dnf install eudev
```

(Some minimal container bases don't include udev; this restores device-node passthrough.)

You can also confirm whipper can see the drive from inside the container:

```bash
distrobox enter ripping
whipper drive list
```

If whipper finds it inside but not from the host, the export wrapper isn't passing through device access. Re-run `distrobox-export --bin /usr/bin/whipper` from inside the container.

### "MusicBrainz error: rate limited"

MusicBrainz throttles unidentified queries. The GUI already sets a User-Agent at launch; if you're still hitting limits, you're sharing an IP with a busy network. Wait a minute and try again.

### AppImage won't launch

Most modern Linux distros have FUSE installed and AppImages just work. On Bazzite, no extra steps. If you see "AppImages require FUSE", either install FUSE or extract the AppImage:

```bash
./whipper-gui-x86_64.AppImage --appimage-extract
./squashfs-root/AppRun
```

### The GUI launches but freezes

Check the log at `~/.local/share/whipper-gui/log.txt`. The most common cause is whipper hanging on a defective disc — cancel from the GUI, eject, try a clean disc.

### `whipper offset find` says my disc isn't in AccurateRip

Try a well-known commercial CD (Pink Floyd, Beatles, Metallica — anything in the top 1000 records). Mix CDs and very obscure pressings often aren't in AccurateRip's database.

### "metaflac: command not found" only when ripping

You exported whipper but not metaflac. Re-enter the container:

```bash
distrobox enter ripping
distrobox-export --bin /usr/bin/metaflac
exit
```

---

## Updating

### Update Whipper GUI

- **AppImage:** download the new release, replace the old file.
- **pipx:** `pipx upgrade whipper-gui`
- **From source:** `git pull && pip install -e .`

### Update whipper or metaflac

```bash
distrobox enter ripping
sudo dnf upgrade whipper flac
exit
```

The host-exported wrappers don't change; they always run whatever is currently inside the container.

### Update the container's base Fedora version

```bash
distrobox enter ripping
sudo dnf system-upgrade download --refresh --releasever=41
sudo dnf system-upgrade reboot   # inside the container only
```

---

## Where things live

| Path | Contents |
|------|----------|
| `~/.local/bin/whipper` | The Distrobox-exported wrapper. **Don't edit.** |
| `~/.local/bin/metaflac` | Same. |
| `~/.config/whipper/whipper.conf` | Drive offsets and cache settings. Shared with the container. |
| `~/.config/whipper-gui/config.toml` | The GUI's own settings (output dir, templates, toggles). |
| `~/.local/share/whipper-gui/log.txt` | GUI log file. Check here when something goes sideways. |
| `~/Music/rips/` *(default)* | Where rips land. Configurable in Settings. |

---

## Documentation for contributors

- [`PLANNING.md`](PLANNING.md) — architecture, module design, design decisions
- [`TASKS.md`](TASKS.md) — active task checklist
- [`DEPENDENCIES.md`](DEPENDENCIES.md) — dependency table, last release dates, replacement plans
- [`CLAUDE.md`](CLAUDE.md) — project rules and conventions (read before contributing)
- [`docs/log-format-comparison.md`](docs/log-format-comparison.md) — whipper-log vs EAC-log field comparison

---

## License

TBD. The project is in early bootstrap and a license has not been chosen yet. PySide6 is LGPL-3.0, which makes MIT, Apache-2.0, BSD, or GPL-3.0 all viable for the project's own code.

See [PLANNING.md §8 KDD-10](PLANNING.md) for the open license question.
