# Checks and tests

```bash
./check.sh
```

Requires Bash, Python 3.9+ and ShellCheck. No npm/pip packages, VSCodium installation, credentials or network are required for local checks.

The script checks shell syntax, runs ShellCheck, validates the tracked JSONC/extension IDs and runs the behavior tests.

| Test file | Coverage |
| --- | --- |
| `test_jsonc.py` | Comments, trailing commas, malformed input and duplicate keys |
| `test_cli.py` | Argument boundaries, custom launchers, timeouts and single-attempt extension operations |
| `test_transfer.py` | Paths with spaces, failed exports, previews, idempotence, mirrors, backups, restoration and injected write failures |

Tests create temporary repository/configuration trees and fake CLI programs. They do not invoke your real editor, modify your settings, install extensions or contact marketplaces. They do not establish compatibility with every VSCodium build or extension.

## CI

The Woodpecker workflow runs the same checks in one Debian container for main-branch pushes, pull requests and manual runs. Installing CI dependencies requires network access; the tests themselves do not.

To use Codeberg's hosted service, complete onboarding if required and enable the repository at [ci.codeberg.org](https://ci.codeberg.org/repos/add). The workflow file does not activate hosting by itself. See [Codeberg's CI documentation](https://docs.codeberg.org/ci/).

[Back to README](../README.md)
