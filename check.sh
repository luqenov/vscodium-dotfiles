#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
for dependency in python3 shellcheck; do
    command -v "$dependency" >/dev/null || { printf 'Missing dependency: %s\n' "$dependency" >&2; exit 1; }
done
for script in export-vscodium.sh install-vscodium.sh check.sh; do bash -n "$script"; done
shellcheck export-vscodium.sh install-vscodium.sh check.sh
python3 -B - <<'PY'
from pathlib import Path
import sys
if sys.version_info < (3, 9):
    raise SystemExit('Python 3.9+ is required.')
sys.path.insert(0, 'lib')
from codium_cli import extension_ids
from transfer import read_entry
from vscodium_config import FILES, validate_entry
for name in FILES:
    entry = read_entry(Path('vscodium') / name)
    if name == 'settings.json' and entry is None:
        raise SystemExit('settings.json is required.')
    validate_entry(name, entry)
entry = read_entry(Path('vscodium/extensions.txt'))
if entry is not None:
    if entry.kind != 'file':
        raise SystemExit('extensions.txt must be a regular file.')
    extension_ids(entry.data.decode('utf-8-sig'))
print('Repository configuration and extension IDs are valid.')
PY
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
