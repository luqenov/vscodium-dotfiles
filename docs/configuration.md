# Personal preferences and installation paths

The repository retains your editor preferences. Transfer scripts do not replace them with generic defaults, install fonts or change marketplace configuration.

## Machine requirements

| Preference | Requirement |
| --- | --- |
| Editor font | `FiraCode Nerd Font` |
| Terminal font | `JetBrainsMono Nerd Font` |
| Theme/icons | Matching extensions from `extensions.txt` |
| Biome | Compatible executable at the configured `/usr/bin/biome` path |
| Python analysis settings | A compatible Python language-analysis extension configured locally |

The default formatter is Prettier, with Biome overrides for JavaScript, TypeScript and TSX. Language-specific choices, save actions and diagnostic preferences remain as tracked in `settings.json`. JSONC validation checks syntax/root types, not every setting or extension's compatibility with a specific editor release.

## Paths and launcher

Without an override, scripts prefer `~/.local/share/appimages/vscodium/AppRun`, setting `APPDIR` to that directory. If it is absent, they look for `codium` on PATH.

```bash
./install-vscodium.sh --appdir "/custom/AppImage directory" --dry-run
./install-vscodium.sh --codium /usr/bin/codium --dry-run
```

The default user-data root is `$XDG_CONFIG_HOME/VSCodium` or `~/.config/VSCodium`. Configuration is transferred under `User/`. Use `--user-data-dir` to override that root; the same path is passed to the CLI. Optional `--extensions-dir` is also forwarded.

The scripts support the Default profile. Named profiles, portable builds and sandbox-specific layouts are not automatically discovered. Do not assume setting the window's default profile changes where these scripts read or write files. Keep `lib/` alongside both entry points.

Private editor state such as `User/History`, workspace/global storage and `.vscdb` databases is excluded from Git. Transfer scripts copy only settings, keybindings, snippets and the extension ID list.

## Extension sources

VSCodium uses Open VSX by default. If an ID fails to install, inspect the CLI error and check the author's published extension sources rather than repeatedly retrying. The script does not automatically query alternative registries.

Where available, a VSIX from the author's release page can be installed manually with the same launcher and data directory:

```bash
codium --user-data-dir "/path/to/user data" --install-extension /path/to/extension.vsix
```

Use your actual launcher and paths. Availability and compatibility vary by extension. See [VSCodium's extension documentation](https://github.com/VSCodium/vscodium/blob/master/docs/extensions.md). The ID-only list intentionally does not pin versions; exporting a VSIX's ID does not preserve its original source or package file.

[Back to README](../README.md)
