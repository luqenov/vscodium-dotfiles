# VSCodium dotfiles

<div align="center">

[![Shell](https://img.shields.io/badge/Shell-Bash-121212?logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![VSCodium](https://img.shields.io/badge/Editor-VSCodium-2F80ED)](https://vscodium.com/)
![Platform](https://img.shields.io/badge/Platform-Linux-18181b)

**Personal settings, recoverable backups and extension installs without repeated requests.**

[Export](docs/export.md) · [Install and restore](docs/install.md) · [Configuration](docs/configuration.md) · [Checks](tests/README.md)

</div>

Keep your VSCodium preferences and installed extension IDs together. Scripts work from any working directory, validate JSONC before copying, and back up changed files before replacement.

## Quick start

Requires Bash and Python 3.9+. No pip packages or sudo are needed. Keep `lib/` alongside both transfer scripts.

```bash
git clone https://codeberg.org/luqenov/vscodium-dotfiles.git
cd vscodium-dotfiles

./install-vscodium.sh --dry-run
./install-vscodium.sh
```

Close VSCodium before applying configuration changes. The default launcher is `~/.local/share/appimages/vscodium/AppRun` when present, otherwise `codium` on PATH. Override it without editing the scripts:

```bash
./install-vscodium.sh --appdir "/path/to/AppImage directory"
./install-vscodium.sh --codium /path/to/codium
```

Only missing extensions are requested. Each is attempted once, with no automatic retry or `--force`. A failed installation appears in the summary and produces a nonzero exit code.

## Export your setup

```bash
./export-vscodium.sh --dry-run
./export-vscodium.sh
git diff -- vscodium/
```

A failed or invalid extension listing leaves the previous repository files intact. Successful exports sort/deduplicate IDs and preserve settings comments. Nothing is committed or pushed automatically.

## Useful options

| Option | Effect |
| --- | --- |
| `--dry-run` | Preview file changes without writing or invoking VSCodium |
| `--skip-extensions` | Transfer configuration only; no CLI or marketplace access |
| `--user-data-dir PATH` | Use `PATH/User` for configuration and pass the same data root to the CLI |
| `--extensions-dir PATH` | Pass a custom extension directory to the CLI |
| `--mirror` | Remove absent managed optional entries and replace the snippet tree exactly |
| `--timeout SECONDS` | Bound each CLI operation; default 180 seconds |
| `--restore BACKUP` | Recover a matching file backup without extension operations |

The default configuration location is `$XDG_CONFIG_HOME/VSCodium/User`, falling back to `~/.config/VSCodium/User`. The scripts target the Default profile and Linux layout. See [configuration requirements](docs/configuration.md) for fonts, Biome and other machine-specific preferences.

## Backups

Changed files get a unique private backup. Unchanged runs create none, and older backups are never overwritten.

- Export backups: `.vscodium-backups/` in this clone, ignored by Git.
- Installation backups: `vscodium-dotfiles-backups/` inside the selected user-data root, alongside `User/`.

```bash
./install-vscodium.sh --restore /absolute/path/to/backup --dry-run
./install-vscodium.sh --restore /absolute/path/to/backup
```

Use `export-vscodium.sh --restore ...` for export backups. Restoration backs up the current affected files before recovering the previous state. Installed extensions are not rolled back; see [recovery details](docs/install.md#recovery).

## Local checks

```bash
./check.sh
```

Requires ShellCheck in addition to Bash/Python. Tests use fake CLI commands and temporary directories; they do not modify your editor or access extension marketplaces. [Checks and CI](tests/README.md).
