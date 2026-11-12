"""Invoke VSCodium with an argument list and no automatic retries."""

import os
from pathlib import Path
import re
import shutil
import subprocess


EXTENSION_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*\.[A-Za-z0-9][A-Za-z0-9_-]*\Z')


def extension_ids(text):
    result = set()
    for line in text.splitlines():
        identifier = line.strip()
        if not identifier:
            continue
        if not EXTENSION_ID.fullmatch(identifier):
            raise ValueError(f'Invalid extension ID: {identifier!r}')
        result.add(identifier.lower())
    return sorted(result)


class Codium:
    def __init__(self, user_data_dir, executable=None, appdir=None, extensions_dir=None, timeout=180):
        self.environment = dict(os.environ)
        if appdir:
            directory = Path(appdir).expanduser().absolute()
            self.executable = str(directory / 'AppRun')
            self.environment['APPDIR'] = str(directory)
        elif executable:
            self.executable = shutil.which(str(executable))
        else:
            directory = Path.home() / '.local/share/appimages/vscodium'
            if (directory / 'AppRun').is_file():
                self.executable = str(directory / 'AppRun')
                self.environment['APPDIR'] = str(directory)
            else:
                self.executable = shutil.which('codium')
        if not self.executable or not os.access(self.executable, os.X_OK):
            raise ValueError('VSCodium executable not found. Use --appdir, --codium or --skip-extensions.')
        self.arguments = ['--user-data-dir', str(user_data_dir)]
        if extensions_dir:
            self.arguments += ['--extensions-dir', str(extensions_dir)]
        self.timeout = timeout

    def run(self, *arguments):
        try:
            result = subprocess.run([self.executable, *self.arguments, *arguments],
                                    env=self.environment, capture_output=True, text=True,
                                    timeout=self.timeout, check=False)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(f'VSCodium command timed out after {self.timeout:g}s; no automatic retry.') from error
        except OSError as error:
            raise RuntimeError(f'Could not start VSCodium: {error}') from error
        if result.returncode:
            detail = result.stderr.strip()[-1000:]
            raise RuntimeError(f'VSCodium command failed (exit {result.returncode}): {detail}')
        return result.stdout

    def installed(self):
        return extension_ids(self.run('--list-extensions'))

    def install_missing(self, requested, installed):
        existing = set(installed)
        added, skipped, failed = [], [], []
        for identifier in requested:
            if identifier in existing:
                skipped.append(identifier)
                continue
            try:
                self.run('--install-extension', identifier)
                added.append(identifier)
                print(f'Installed: {identifier}')
            except RuntimeError as error:
                failed.append(identifier)
                print(f'Failed: {identifier}: {error}')
        print(f'Extensions: {len(added)} installed, {len(skipped)} already present, {len(failed)} failed.')
        if failed:
            print('Failed IDs: ' + ', '.join(failed))
        return not failed
