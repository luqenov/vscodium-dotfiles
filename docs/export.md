# Export VSCodium configuration

`export-vscodium.sh` writes into the `vscodium/` directory of its own clone, regardless of your working directory.

```bash
./export-vscodium.sh --dry-run
./export-vscodium.sh
```

## Behavior

Reads `settings.json`, optional `keybindings.json` and optional `snippets/` from the selected `User/` directory. Settings must be a JSONC object and keybindings an array; `.json`/`.code-snippets` files under snippets must be objects. Comments and trailing commas are accepted without reformatting your files.

A live export queries `--list-extensions` once, validates the output and writes sorted, unique IDs to `extensions.txt`. A failed command or malformed output stops the export before managed files change. Extension versions and enabled/disabled state are not recorded by the ID list.

A dry run never launches VSCodium. It previews configuration changes and reports that the extension list will be refreshed during a live export; it cannot determine that list without a CLI query.

## Custom installation

```bash
./export-vscodium.sh --appdir "/path/to/AppImage directory"
./export-vscodium.sh --codium /path/to/codium \
  --user-data-dir "/path/to/user data" --extensions-dir "/path/to/extensions"
```

Use `--skip-extensions` to copy configuration without a launcher or extension query. The existing repository extension list remains untouched.

Paths default to the Linux AppImage/Default-profile setup described in the [README](../README.md). Explicit `--user-data-dir` paths may be relative to your current directory; `XDG_CONFIG_HOME`, when used, must be absolute.

## Copy or mirror

Default exports keep absent optional destination entries and merge snippet trees, including hidden files. `--mirror` removes missing optional managed entries and replaces snippets exactly. It never removes repository scripts, documentation or unrelated configuration entries. A source `settings.json` is always required.

```bash
./export-vscodium.sh --mirror --dry-run
```

Empty directories are transferred on disk; Git does not track empty directories without placeholder files. Managed symlinks and overlapping configuration/repository roots are refused.

## Recovery

Every changed export prints a unique `.vscodium-backups/` path. It contains prior affected entries and records which files did not exist before the operation. Backups are ignored by Git but may still contain private local configuration; keep them private.

```bash
./export-vscodium.sh --restore /absolute/path/to/clone/.vscodium-backups/BACKUP --dry-run
./export-vscodium.sh --restore /absolute/path/to/clone/.vscodium-backups/BACKUP
```

Restore accepts only backups matching this clone and operation. Review `git diff` before publishing, including task commands, private paths and any credentials stored in settings.

[Back to README](../README.md)
