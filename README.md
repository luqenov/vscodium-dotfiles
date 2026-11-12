# VSCodium dotfiles

My personal VSCodium setup (AppImage build), kept in sync across machines.

## What's here

- `vscodium/extensions.txt` — list of installed extension IDs (one per line, no version)
- `vscodium/settings.json` — user settings
- `vscodium/keybindings.json` — custom keybindings (if present)
- `vscodium/snippets/` — custom snippets (if present)
- `export-vscodium.sh` — dumps your current VSCodium setup into this repo
- `install-vscodium.sh` — restores extensions + settings from this repo onto a machine

Both scripts assume VSCodium is installed as an AppImage under:
```
~/.local/share/appimages/vscodium
```
(the default path used by the hezkore AppImage installer). If your AppImage
lives somewhere else, edit the `APPDIR` variable at the top of each script.

## Backing up (after changing settings/extensions)

```bash
./export-vscodium.sh
git add vscodium/
git commit -m "vscodium: update settings/extensions"
git push
```

## Restoring on a new machine

1. Install VSCodium (AppImage) and open it once, then close every window.
2. Clone this repo and run:
   ```bash
   ./install-vscodium.sh
   ```

## Known gotcha: extensions not on Open VSX

VSCodium uses **Open VSX** as its default extension marketplace instead of
Microsoft's official Marketplace. A few extensions (mostly ones owned by
Microsoft/GitHub) are only published on the official Marketplace and won't
install through `install-vscodium.sh`. If an extension in `extensions.txt`
fails to install, check whether it's available on
[open-vsx.org](https://open-vsx.org) — if not, you'll need to download its
`.vsix` from the official Marketplace and install it manually with
`--install-extension path/to/file.vsix`.
