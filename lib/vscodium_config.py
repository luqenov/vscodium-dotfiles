#!/usr/bin/env python3
"""Export or install VSCodium files with optional, bounded extension operations."""

import argparse
import math
import os
from pathlib import Path
import signal
import sys

from codium_cli import Codium, extension_ids
import jsonc
from transfer import Entry, apply_plan, overlay, read_entry, restore_plan


REPO = Path(__file__).resolve().parents[1]
FILES = ('settings.json', 'keybindings.json', 'snippets')


def validate_entry(name, entry):
    if entry is None:
        return
    if name == 'snippets':
        if entry.kind != 'directory':
            raise ValueError('snippets must be a directory')
        for child_name, child in entry.children.items():
            if child.kind == 'directory':
                validate_entry(name, child)
            elif child_name.endswith(('.json', '.code-snippets')):
                jsonc.require_type(child.data.decode('utf-8-sig'), dict)
    else:
        if entry.kind != 'file':
            raise ValueError(f'{name} must be a regular file')
        expected = list if name == 'keybindings.json' else dict
        jsonc.require_type(entry.data.decode('utf-8-sig'), expected)


def build_plan(source, destination, mirror):
    incoming = {name: read_entry(source / name) for name in FILES}
    if incoming['settings.json'] is None:
        raise ValueError(f'Missing required settings.json: {source}')
    for name, entry in incoming.items():
        validate_entry(name, entry)
    plan = {}
    for name, desired in incoming.items():
        previous = read_entry(destination / name)
        if desired is None and not mirror:
            continue
        if desired is not None and name == 'snippets' and not mirror:
            desired = overlay(previous, desired)
        if previous != desired:
            plan[name] = (previous, desired)
    return plan


def requested_extensions(path):
    entry = read_entry(path)
    if entry is None:
        print('Note: extensions.txt is absent; only configuration files will be installed.')
        return []
    if entry.kind != 'file':
        raise ValueError('extensions.txt must be a regular file')
    return extension_ids(entry.data.decode('utf-8-sig'))


def absolute_path(value):
    return Path(value).expanduser().absolute()


def default_user_data_dir():
    base = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')
    if not base.is_absolute():
        raise ValueError('XDG_CONFIG_HOME must be an absolute path')
    return base / 'VSCodium'


def positive_timeout(value):
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError('Timeout must be a positive, finite number')
    return seconds


def interrupted(signum, _frame):
    raise KeyboardInterrupt(f'Interrupted by signal {signum}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('export', 'install'))
    parser.add_argument('--dry-run', action='store_true', help='Preview files without running VSCodium or writing anything')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--mirror', action='store_true', help='Mirror managed configuration files and snippet trees')
    mode.add_argument('--restore', type=absolute_path, metavar='BACKUP', help='Restore a backup without extension operations')
    command = parser.add_mutually_exclusive_group()
    command.add_argument('--appdir', type=absolute_path, help='Directory containing AppRun')
    command.add_argument('--codium', help='VSCodium executable path or command name')
    parser.add_argument('--user-data-dir', type=absolute_path, help='VSCodium data root; configuration is under User/')
    parser.add_argument('--extensions-dir', type=absolute_path, help='Optional extension root passed to VSCodium')
    parser.add_argument('--skip-extensions', action='store_true', help='Transfer files without invoking VSCodium')
    parser.add_argument('--timeout', type=positive_timeout, default=180, help='Seconds per CLI operation (default: 180; no retries)')
    args = parser.parse_args(argv)
    data = args.user_data_dir or default_user_data_dir()
    user = data / 'User'
    if user.is_symlink():
        raise ValueError(f'Symlinked User directory is not supported: {user}')
    user = user.resolve()
    repository = REPO / 'vscodium'
    if repository.is_symlink():
        raise ValueError('The repository configuration directory must not be a symlink')
    if user == repository or user in repository.parents or repository in user.parents:
        raise ValueError('Repository and user configuration paths must not overlap')
    source, destination = (user, repository) if args.operation == 'export' else (repository, user)
    backups = REPO / '.vscodium-backups' if args.operation == 'export' else user.parent / 'vscodium-dotfiles-backups'
    allowed = FILES + (('extensions.txt',) if args.operation == 'export' else ())
    if args.restore:
        plan = restore_plan(args.operation, destination, args.restore, allowed)
        apply_plan(args.operation, destination, plan, backups, args.dry_run)
        print('Restoration covers configuration files only; installed extensions are unchanged.')
        return 0
    plan = build_plan(source, destination, args.mirror)
    client = None
    requested = []
    installed = []
    if not args.skip_extensions:
        if args.operation == 'install':
            requested = requested_extensions(repository / 'extensions.txt')
        if args.dry_run:
            if args.operation == 'export':
                print('Extensions: extensions.txt will be refreshed when applied; the CLI is not queried in previews.')
            else:
                print(f'Extensions: {len(requested)} requested; only missing IDs will be installed when applied.')
        elif args.operation == 'export' or requested:
            client = Codium(data, executable=args.codium, appdir=args.appdir,
                            extensions_dir=args.extensions_dir, timeout=args.timeout)
            installed = client.installed()
            if args.operation == 'export':
                previous = read_entry(repository / 'extensions.txt')
                desired = Entry('file', 0o644, ''.join(identifier + '\n' for identifier in installed).encode())
                if desired != previous:
                    plan['extensions.txt'] = (previous, desired)
    apply_plan(args.operation, destination, plan, backups, args.dry_run)
    if args.dry_run:
        return 0
    if args.operation == 'install' and client:
        if not client.install_missing(requested, installed):
            print('Configuration files were applied. Some extensions failed; see the summary above.')
            return 1
    if args.skip_extensions:
        print('Extension operations skipped.')
    print('Done. Review the exported diff.' if args.operation == 'export' else 'Done. Open VSCodium to check your settings.')
    return 0


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, interrupted)
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, UnicodeError) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('Interrupted. Inspect the reported file backup and any partially installed extensions.', file=sys.stderr)
        sys.exit(130)
