import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from codium_cli import Codium, extension_ids


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='codium cli ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.appdir = self.root / 'app dir; literal'
        self.appdir.mkdir()
        self.log = self.root / 'calls.jsonl'
        self.app = self.appdir / 'AppRun'
        self.app.write_text('''#!/usr/bin/env python3
import json, os, sys, time
with open(os.environ['CALL_LOG'], 'a') as log:
    log.write(json.dumps({'args':sys.argv[1:],'appdir':os.environ.get('APPDIR')})+'\\n')
if os.environ.get('STALL') == 'yes': time.sleep(2)
if '--list-extensions' in sys.argv:
    if os.environ.get('FAIL_LIST') == 'yes': sys.exit(7)
    print('publisher.present')
if '--install-extension' in sys.argv and sys.argv[-1] == 'publisher.broken': sys.exit(8)
''')
        self.app.chmod(0o755)
        self.env = mock.patch.dict(os.environ, CALL_LOG=str(self.log))
        self.env.start()
        self.addCleanup(self.env.stop)

    def cli(self, **options):
        return Codium(self.root / 'user data', appdir=self.appdir, **options)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_paths_are_single_arguments_without_shell_evaluation(self):
        client = self.cli(extensions_dir=self.root / 'extension dir')
        self.assertEqual(client.installed(), ['publisher.present'])
        call = self.calls()[0]
        self.assertEqual(call['args'], ['--user-data-dir', str(self.root / 'user data'),
                                       '--extensions-dir', str(self.root / 'extension dir'), '--list-extensions'])
        self.assertEqual(call['appdir'], str(self.appdir))

    def test_explicit_executable(self):
        client = Codium(self.root / 'user', executable=self.app)
        self.assertEqual(client.installed(), ['publisher.present'])

    def test_only_missing_extensions_are_attempted_once(self):
        client = self.cli()
        installed = client.installed()
        result = client.install_missing(['publisher.broken', 'publisher.new', 'publisher.present'], installed)
        self.assertFalse(result)
        calls = self.calls()
        self.assertEqual(sum('--list-extensions' in c['args'] for c in calls), 1)
        installs = [c['args'][-1] for c in calls if '--install-extension' in c['args']]
        self.assertEqual(installs, ['publisher.broken', 'publisher.new'])
        self.assertTrue(all('--force' not in c['args'] for c in calls))

    def test_failed_list_is_an_error(self):
        with mock.patch.dict(os.environ, FAIL_LIST='yes'):
            with self.assertRaises(RuntimeError):
                self.cli().installed()
        self.assertEqual(len(self.calls()), 1)

    def test_timeout_has_no_retry(self):
        with mock.patch.dict(os.environ, STALL='yes'):
            with self.assertRaises(RuntimeError):
                self.cli(timeout=0.2).installed()
        self.assertEqual(len(self.calls()), 1)

    def test_ids_are_validated_normalized_and_deduplicated(self):
        self.assertEqual(extension_ids('Publisher.Name\r\npublisher.name\n\npublisher.other'),
                         ['publisher.name', 'publisher.other'])
        for identifier in ('--help', 'publisher.name;touch file', 'publisher.name@1.0', 'unknown'):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                extension_ids(identifier)


if __name__ == '__main__':
    unittest.main()
