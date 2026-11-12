"""Stage managed configuration entries and keep persistent recovery snapshots."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile


@dataclass
class Entry:
    kind: str
    mode: int
    data: bytes = b''
    children: dict = field(default_factory=dict)


def read_entry(path):
    if path.is_symlink():
        raise ValueError(f'Symlinks are not managed: {path}')
    if not path.exists():
        return None
    mode = path.stat().st_mode & 0o777
    if path.is_file():
        return Entry('file', mode, path.read_bytes())
    if path.is_dir():
        return Entry('directory', mode, children={
            child.name: read_entry(child) for child in sorted(path.iterdir())
        })
    raise ValueError(f'Not a regular file or directory: {path}')


def write_entry(path, entry):
    if entry.kind == 'file':
        path.write_bytes(entry.data)
    else:
        path.mkdir()
        for name, child in entry.children.items():
            write_entry(path / name, child)
    path.chmod(entry.mode)


def remove_entry(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def overlay(current, incoming):
    if current is None or current.kind != 'directory' or incoming.kind != 'directory':
        return incoming
    children = dict(current.children)
    for name, entry in incoming.children.items():
        children[name] = overlay(children.get(name), entry)
    return Entry('directory', current.mode, children=children)



def save_backup(operation, destination, plan, backup_root):
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-')
    backup = Path(tempfile.mkdtemp(prefix=stamp, dir=backup_root))
    (backup / 'files').mkdir(mode=0o700)
    for name, (previous, _) in plan.items():
        if previous is not None:
            write_entry(backup / 'files' / name, previous)
    metadata = {
        'version': 1, 'operation': operation, 'destination': str(destination),
        'entries': {name: previous is not None for name, (previous, _) in plan.items()},
    }
    (backup / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return backup


def replace_entry(destination, name, entry, stage):
    prepared = stage / 'new' / name
    previous = stage / 'old' / name
    target = destination / name
    if entry is not None and entry.kind == 'file' and (not target.exists() or target.is_file()):
        os.replace(prepared, target)
        return
    if target.exists():
        os.replace(target, previous)
    try:
        if entry is not None:
            os.replace(prepared, target)
    except BaseException:
        if previous.exists():
            os.replace(previous, target)
        raise


def apply_plan(operation, destination, plan, backup_root, dry_run):
    if not plan:
        print('Already up to date. No files changed.')
        return None
    for name, (previous, desired) in plan.items():
        action = 'remove' if desired is None else ('create' if previous is None else 'update')
        print(f'{action}: {destination / name}')
    if dry_run:
        print('Dry run: no files, directories or backups created.')
        return None
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.vscodium-stage-', dir=destination) as temporary:
        stage = Path(temporary)
        (stage / 'new').mkdir()
        (stage / 'old').mkdir()
        (stage / 'rollback').mkdir()
        for name, (_, desired) in plan.items():
            if desired is not None:
                write_entry(stage / 'new' / name, desired)
        # WARN: stop if another process changed a target after the plan was prepared.
        for name, (previous, _) in plan.items():
            if read_entry(destination / name) != previous:
                raise ValueError(f'Target changed during planning: {destination / name}')
        backup = save_backup(operation, destination, plan, backup_root)
        print(f'Backup: {backup}')
        completed = []
        try:
            for name, (_, desired) in plan.items():
                completed.append(name)
                replace_entry(destination, name, desired, stage)
        except BaseException:
            errors = []
            for name in reversed(completed):
                try:
                    previous = stage / 'old' / name
                    if previous.exists():
                        remove_entry(destination / name)
                        os.replace(previous, destination / name)
                    elif plan[name][0] is None:
                        remove_entry(destination / name)
                    elif plan[name][0].kind == 'file':
                        saved = stage / 'rollback' / name
                        write_entry(saved, plan[name][0])
                        os.replace(saved, destination / name)
                except OSError as error:
                    errors.append(str(error))
            if errors:
                print(f'Rollback incomplete. Restore from {backup}: {errors}', file=sys.stderr)
            raise
    return backup


def restore_plan(operation, destination, backup, allowed):
    if (backup.is_symlink() or (backup / 'manifest.json').is_symlink()
            or (backup / 'files').is_symlink()):
        raise ValueError('Symlinked backups are not supported')
    metadata = json.loads((backup / 'manifest.json').read_text())
    if (metadata.get('version') != 1 or metadata.get('operation') != operation
            or metadata.get('destination') != str(destination)):
        raise ValueError('Backup does not match this operation and destination')
    entries = metadata.get('entries')
    if not isinstance(entries, dict) or not entries:
        raise ValueError('Backup manifest has no entries')
    plan = {}
    for name, present in entries.items():
        if name not in allowed or not isinstance(present, bool):
            raise ValueError('Invalid backup manifest entry')
        desired = read_entry(backup / 'files' / name) if present else None
        if present and desired is None:
            raise ValueError(f'Backup entry missing: {name}')
        current = read_entry(destination / name)
        if desired != current:
            plan[name] = (current, desired)
    return plan
