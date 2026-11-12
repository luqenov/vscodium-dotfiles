#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
# shellcheck source=tests/check-output.sh
source tests/check-output.sh
check_init vscodium-dotfiles "$@"

check_syntax() {
    for script in export-vscodium.sh install-vscodium.sh check.sh tests/check-output.sh; do bash -n "$script"; done
}

check_step 'Required tools' check_dependencies python3 shellcheck
check_step 'Shell syntax' check_syntax
check_step 'Shell script quality' shellcheck -x export-vscodium.sh install-vscodium.sh check.sh tests/check-output.sh
check_step 'Configuration files and extension list' python3 -B - <<'PY'
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
check_step 'Extension commands and configuration recovery' python3 -B -m unittest discover -s tests "$CHECK_TEST_FLAG"
check_finish
