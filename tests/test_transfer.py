import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
import transfer


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='codium config ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo with spaces'
        self.repo.mkdir()
        (self.repo / 'vscodium').mkdir()
        shutil.copytree(ROOT / 'lib', self.repo / 'lib', ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('export-vscodium.sh', 'install-vscodium.sh'):
            shutil.copy2(ROOT / name, self.repo / name)
        self.data = self.root / 'data with spaces; literal'
        self.user = self.data / 'User'
        self.user.mkdir(parents=True)
        self.appdir = self.root / 'AppImage directory'
        self.appdir.mkdir()
        self.log = self.root / 'calls.jsonl'
        self.state = self.root / 'extensions.json'
        self.state.write_text('["publisher.present"]')
        app = self.appdir / 'AppRun'
        app.write_text('''#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
args = sys.argv[1:]
with open(os.environ['CALL_LOG'], 'a') as log: log.write(json.dumps(args)+'\\n')
state = Path(os.environ['EXT_STATE'])
installed = json.loads(state.read_text())
if '--list-extensions' in args:
    if os.environ.get('FAIL_LIST') == 'yes': sys.exit(7)
    if os.environ.get('INVALID_LIST') == 'yes': print('unexpected output'); sys.exit(0)
    print('\\n'.join(installed))
if '--install-extension' in args:
    name = args[args.index('--install-extension') + 1]
    if name == 'publisher.broken': sys.exit(8)
    installed.append(name)
    state.write_text(json.dumps(installed))
''')
        app.chmod(0o755)
        self.env = dict(os.environ, CALL_LOG=str(self.log), EXT_STATE=str(self.state),
                        HOME=str(self.root / 'home'), XDG_CONFIG_HOME=str(self.root / 'config'),
                        PYTHONDONTWRITEBYTECODE='1')
        (self.repo / 'vscodium/settings.json').write_text('// repo\n{"theme":"custom",}\n')
        (self.repo / 'vscodium/extensions.txt').write_text('publisher.present\npublisher.new')
        (self.user / 'settings.json').write_text('{"theme":"local"}\n')

    def cli(self, operation, *args, success=True):
        result = subprocess.run(['bash', str(self.repo / f'{operation}-vscodium.sh'),
                                 '--user-data-dir', str(self.data), '--appdir', str(self.appdir),
                                 *map(str, args)], env=self.env, cwd=self.root,
                                capture_output=True, text=True, timeout=10)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def backups(self, operation):
        root = self.repo / '.vscodium-backups' if operation == 'export' else self.data / 'vscodium-dotfiles-backups'
        return sorted(root.iterdir()) if root.exists() else []

    def test_export_uses_repo_location_from_another_directory(self):
        self.cli('export')
        self.assertEqual((self.repo / 'vscodium/settings.json').read_text(), '{"theme":"local"}\n')
        self.assertEqual((self.repo / 'vscodium/extensions.txt').read_text(), 'publisher.present\n')
        self.assertFalse((self.root / 'vscodium').exists())
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(len(self.backups('export')), 1)

    def test_failed_or_invalid_extension_listing_keeps_all_prior_files(self):
        original = (self.repo / 'vscodium/extensions.txt').read_bytes()
        original_settings = (self.repo / 'vscodium/settings.json').read_bytes()
        for failure in ('FAIL_LIST', 'INVALID_LIST'):
            with self.subTest(failure=failure):
                self.env[failure] = 'yes'
                self.cli('export', success=False)
                self.env.pop(failure)
                self.assertEqual((self.repo / 'vscodium/extensions.txt').read_bytes(), original)
                self.assertEqual((self.repo / 'vscodium/settings.json').read_bytes(), original_settings)
                self.assertEqual(self.backups('export'), [])

    def test_install_skips_present_ids_and_handles_missing_final_newline(self):
        self.cli('install')
        installs = [args[-1] for args in self.calls() if '--install-extension' in args]
        self.assertEqual(installs, ['publisher.new'])
        self.assertEqual(sum('--list-extensions' in args for args in self.calls()), 1)
        self.assertEqual((self.user / 'settings.json').read_bytes(), (self.repo / 'vscodium/settings.json').read_bytes())

    def test_repeated_install_is_idempotent(self):
        self.cli('install')
        backups = self.backups('install')
        self.log.unlink()
        result = self.cli('install')
        self.assertIn('Already up to date', result.stdout)
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(self.backups('install'), backups)

    def test_failed_extension_is_reported_with_nonzero_exit_without_retry(self):
        (self.repo / 'vscodium/extensions.txt').write_text('publisher.broken\npublisher.new\npublisher.present\n')
        result = self.cli('install', success=False)
        self.assertIn('1 installed, 1 already present, 1 failed', result.stdout)
        installs = [args[-1] for args in self.calls() if '--install-extension' in args]
        self.assertEqual(installs, ['publisher.broken', 'publisher.new'])
        self.assertIn('Configuration files were applied', result.stdout)
        self.assertEqual(len(self.backups('install')), 1)

    def test_dry_runs_never_invoke_cli_or_create_backups(self):
        repo_before = (self.repo / 'vscodium/settings.json').read_bytes()
        user_before = (self.user / 'settings.json').read_bytes()
        for operation in ('export', 'install'):
            self.cli(operation, '--dry-run')
            self.assertEqual(self.backups(operation), [])
        self.assertFalse(self.log.exists())
        self.assertEqual((self.repo / 'vscodium/settings.json').read_bytes(), repo_before)
        self.assertEqual((self.user / 'settings.json').read_bytes(), user_before)
        self.assertFalse(list(self.root.rglob('.vscodium-stage-*')))

    def test_config_only_export_preserves_extensions_without_calling_cli(self):
        previous = (self.repo / 'vscodium/extensions.txt').read_bytes()
        self.cli('export', '--skip-extensions')
        self.assertFalse(self.log.exists())
        self.assertEqual((self.repo / 'vscodium/extensions.txt').read_bytes(), previous)

    def test_empty_extension_list_needs_no_cli(self):
        (self.repo / 'vscodium/extensions.txt').write_text('')
        self.cli('install')
        self.assertFalse(self.log.exists())

    def test_hidden_snippets_merge_and_mirror(self):
        (self.repo / 'vscodium/snippets').mkdir()
        (self.repo / 'vscodium/snippets/.hidden').write_text('new')
        (self.user / 'snippets').mkdir()
        (self.user / 'snippets/old.code-snippets').write_text('{}')
        (self.user / 'keybindings.json').write_text('[]')
        self.cli('install', '--skip-extensions')
        self.assertTrue((self.user / 'snippets/old.code-snippets').exists())
        self.assertEqual((self.user / 'snippets/.hidden').read_text(), 'new')
        self.assertTrue((self.user / 'keybindings.json').exists())
        self.cli('install', '--skip-extensions', '--mirror')
        self.assertFalse((self.user / 'snippets/old.code-snippets').exists())
        self.assertFalse((self.user / 'keybindings.json').exists())

    def test_backup_restores_all_files_and_absence_of_new_entries(self):
        original = (self.user / 'settings.json').read_bytes()
        (self.repo / 'vscodium/keybindings.json').write_text('[]')
        (self.repo / 'vscodium/snippets').mkdir()
        (self.repo / 'vscodium/snippets/example.code-snippets').write_text('{}')
        self.cli('install', '--skip-extensions')
        backup = self.backups('install')[0]
        self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
        self.cli('install', '--restore', backup, '--dry-run')
        self.cli('install', '--restore', backup)
        self.assertEqual((self.user / 'settings.json').read_bytes(), original)
        self.assertFalse((self.user / 'keybindings.json').exists())
        self.assertFalse((self.user / 'snippets').exists())
        self.assertEqual(len(self.backups('install')), 2)
        self.assertFalse(self.log.exists())

    def test_export_restore_recovers_previous_extension_list(self):
        previous = (self.repo / 'vscodium/extensions.txt').read_bytes()
        self.cli('export')
        self.cli('export', '--restore', self.backups('export')[0])
        self.assertEqual((self.repo / 'vscodium/extensions.txt').read_bytes(), previous)
        self.assertEqual(len(self.calls()), 1)

    def test_invalid_inputs_fail_before_cli_or_writes(self):
        original = (self.user / 'settings.json').read_bytes()
        for name, text in (('settings.json', '{"bad":}'), ('keybindings.json', '{}'),
                           ('extensions.txt', '--help'), ('snippets/bad.code-snippets', '{,}')):
            with self.subTest(name=name):
                path = self.repo / 'vscodium' / name
                saved = path.read_bytes() if path.exists() else None
                path.parent.mkdir(exist_ok=True)
                path.write_text(text)
                self.cli('install', success=False)
                self.assertEqual((self.user / 'settings.json').read_bytes(), original)
                self.assertFalse(self.log.exists())
                self.assertEqual(self.backups('install'), [])
                if saved is None:
                    path.unlink()
                else:
                    path.write_bytes(saved)

    def test_symlink_source_or_destination_is_refused(self):
        outside = self.root / 'outside'
        outside.write_text('keep')
        (self.user / 'settings.json').unlink()
        (self.user / 'settings.json').symlink_to(outside)
        self.cli('install', '--skip-extensions', success=False)
        self.assertEqual(outside.read_text(), 'keep')
        self.assertFalse(self.backups('install'))

    def test_restore_rejects_foreign_destination_and_traversal(self):
        self.cli('install', '--skip-extensions')
        backup = self.backups('install')[0]
        manifest = backup / 'manifest.json'
        metadata = json.loads(manifest.read_text())
        metadata['destination'] = '/foreign'
        manifest.write_text(json.dumps(metadata))
        self.cli('install', '--restore', backup, success=False)
        metadata['destination'] = str(self.user)
        metadata['entries'] = {'../outside': False}
        manifest.write_text(json.dumps(metadata))
        self.cli('install', '--restore', backup, success=False)

    def test_default_xdg_config_location_without_appimage(self):
        result = subprocess.run(['bash', str(self.repo / 'install-vscodium.sh'), '--skip-extensions'],
                                env=self.env, cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        installed = self.root / 'config/VSCodium/User/settings.json'
        self.assertEqual(installed.read_bytes(), (self.repo / 'vscodium/settings.json').read_bytes())
        self.assertFalse(self.log.exists())

    def test_missing_executable_preview_creates_no_config_directory(self):
        (self.user / 'settings.json').unlink()
        self.user.rmdir()
        shutil.rmtree(self.appdir)
        result = self.cli('install', '--dry-run')
        self.assertIn('create:', result.stdout)
        self.assertFalse(self.user.exists())
        self.assertFalse(self.log.exists())


class TransactionTests(unittest.TestCase):
    def test_mid_transfer_failure_rolls_back_files_atomically(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / 'User'
            target.mkdir()
            (target / 'settings.json').write_text('{"old":true}')
            (target / 'keybindings.json').write_text('[]')
            before = {name: transfer.read_entry(target / name) for name in ('settings.json', 'keybindings.json')}
            plan = {name: (entry, transfer.Entry('file', 0o600, b'{}')) for name, entry in before.items()}
            replace = transfer.os.replace

            def fail_one(source, destination):
                if Path(source).parent.name == 'new' and Path(destination).name == 'keybindings.json':
                    raise OSError('simulated failure')
                return replace(source, destination)

            with mock.patch.object(transfer.os, 'replace', side_effect=fail_one):
                with self.assertRaises(OSError):
                    transfer.apply_plan('install', target, plan, root / 'backups', False)
            for name, entry in before.items():
                self.assertEqual(transfer.read_entry(target / name), entry)
            self.assertEqual(len(list((root / 'backups').iterdir())), 1)
            self.assertFalse(list(target.glob('.vscodium-stage-*')))


if __name__ == '__main__':
    unittest.main()
