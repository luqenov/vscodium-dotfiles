# Install and restore VSCodium configuration

Close VSCodium before applying changes. The script installs configuration and missing extensions, not VSCodium itself.

```bash
./install-vscodium.sh --dry-run
./install-vscodium.sh
```

## Configuration transfer

All source files are validated and replacement content is staged before managed files change. Settings/keybindings are copied exactly, including comments. Optional snippets are merged by default, preserving destination-only files. Missing optional source entries leave the destination untouched.

```bash
# Apply only files, without launching VSCodium.
./install-vscodium.sh --skip-extensions

# Preview exact mirroring of the managed entries.
./install-vscodium.sh --mirror --dry-run
```

`--mirror` removes optional entries absent from the source and replaces snippets exactly. Other data in the selected `User/` directory is preserved. A missing or invalid source `settings.json` is an error.

## Extensions

IDs in `extensions.txt` are validated, normalized and deduplicated. Blank lines and a missing final newline are supported. The script queries installed extensions once, then attempts each missing ID once. Present IDs are skipped; they are not updated or re-enabled by this script.

No `--force`, retry loop, polling or marketplace fallback is used. Each CLI operation has a configurable timeout, defaulting to 180 seconds. A failed listing stops before configuration files are changed. Install failures are summarized and return a nonzero exit code; other missing IDs are still attempted once.

When an individual install fails, applied configuration files and successful extension installations remain in place. `--skip-extensions` allows file restoration independently. Missing/empty extension lists perform no extension installation. See [extension sources](configuration.md#extension-sources) when an ID is unavailable.

## Recovery

Changed configuration entries are backed up under `vscodium-dotfiles-backups/` in the selected user-data root. Each backup has a unique name and a private top-level directory. Older backups are retained until you remove them manually.

```bash
./install-vscodium.sh --restore /absolute/path/to/backup --dry-run
./install-vscodium.sh --restore /absolute/path/to/backup
```

Restoring recovers prior entries and removes those created by the original transfer. It also saves the current affected state in a new backup. Use the same `--user-data-dir` as the original operation. Backups must match the operation and destination; moving configuration roots may require manual recovery.

File replacement uses atomic rename. Directory replacement moves the old tree aside first. Ordinary transfer errors trigger rollback, with a persistent backup available if recovery fails. Changes across multiple files are not one filesystem transaction. After a power failure or `SIGKILL`, inspect the persistent backup and any `.vscodium-stage-*` directory before cleanup.

Keep the editor closed during transfers. The scripts check targets after preparing the plan, but cannot lock out other applications. Extension installs are separate operations: file backups do not uninstall, downgrade or otherwise restore extensions.

[Back to README](../README.md)
