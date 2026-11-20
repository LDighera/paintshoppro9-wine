"""Source-level checks only; no Wine, desktop, network or application is launched."""
import argparse
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psp9 as P


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='psp-portable-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.wine = self.root/'wine'
        (self.wine/'bin').mkdir(parents=True)
        for name in ('wine', 'wineserver'):
            (self.wine/'bin'/name).touch()
        self.state = self.root/'state'
        self.home = self.root/'home'
        self.home.mkdir()
        self.media = self.home/'Pictures'
        self.media.mkdir()
        self.package = self.root/'package'
        (self.package/'build').mkdir(parents=True)
        (self.package/'session.sh').touch()
        for name in ('bootstrap.exe', 'psp-worker-helper.dll', 'worker-test.exe',
                     'unload-probe.dll', 'reject-helper.dll'):
            (self.package/'build'/name).touch()
        self.patcher = patch.object(P, 'PACKAGE', self.package)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.mounts = patch.object(P, 'mount_identity', return_value={'target': '/', 'filesystem': 'fixture', 'root': '/', 'identity': 'synthetic'})
        self.mount_mock = self.mounts.start()
        self.addCleanup(self.mounts.stop)

    def configure(self):
        args = argparse.Namespace(state=str(self.state), wine=str(self.wine), media=[str(self.media)])
        with patch.object(P, 'ordinary_user'), patch.object(P.Path, 'home', return_value=self.home):
            P.initialize_settings(args)

    def test_create_private_settings_does_not_launch(self):
        with patch.object(P.os, 'execv') as execute, patch.object(P.subprocess, 'run') as run:
            self.configure()
            execute.assert_not_called()
            run.assert_not_called()
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.state/'settings.json').stat().st_mode), 0o600)
        self.assertEqual(list((self.state/'prefix').iterdir()), [])

    def test_existing_state_is_never_replaced(self):
        self.configure()
        before = (self.state/'settings.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.configure()
        self.assertEqual((self.state/'settings.json').read_bytes(), before)

    def test_root_is_rejected(self):
        with patch.object(P.os, 'getuid', return_value=0), self.assertRaisesRegex(ValueError, 'do not use sudo'):
            P.ordinary_user()

    def test_media_must_not_expose_home_or_runtime(self):
        for folder in (self.home, self.root, self.wine, self.package):
            with self.subTest(folder=folder), self.assertRaises(ValueError):
                P.check_layout(self.wine, self.state, [folder], self.home)

    def test_media_must_not_overlap(self):
        child = self.media/'child'
        child.mkdir()
        for items in ([self.media, self.media], [self.media, child]):
            with self.assertRaises(ValueError):
                P.check_layout(self.wine, self.state, items, self.home)

    def test_home_secret_and_ancestor_directories_rejected(self):
        for folder in (self.home, self.home.parent, self.home/'.ssh', self.home/'.config'/'nested', self.home/'.aws'):
            with self.subTest(folder=folder), self.assertRaises(ValueError):
                P.user_folder(folder, self.home)
        P.user_folder(self.home/'Downloads'/'Installer', self.home)

    def test_symlink_and_relative_paths_rejected(self):
        alias = self.root/'alias'
        alias.symlink_to(self.media)
        for value in (str(alias), '../relative', str(self.media)+'\n'):
            with self.assertRaises(ValueError):
                P.clean_path(value)

    def test_settings_reject_unknown_keys_and_duplicates(self):
        self.configure()
        file = self.state/'settings.json'
        original = file.read_text()
        data = json.loads(original)
        data['password'] = 'synthetic-private-marker'
        file.write_text(json.dumps(data))
        with patch.object(P.Path, 'home', return_value=self.home), self.assertRaises(ValueError) as error:
            P.load_settings(str(self.state))
        self.assertNotIn('synthetic-private-marker', str(error.exception))
        file.write_text(original.replace('"version": 1', '"version": 1, "version": 1'))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            P.load_settings(str(self.state))

    def test_settings_permissions_and_prefix_symlinks_rejected(self):
        self.configure()
        path = self.state/'settings.json'
        path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, '0600'):
            P.load_settings(str(self.state))
        path.chmod(0o600)
        (self.state/'prefix').rmdir()
        (self.state/'prefix').symlink_to(self.media)
        with patch.object(P.Path, 'home', return_value=self.home), self.assertRaisesRegex(ValueError, 'prefix/home'):
            P.load_settings(str(self.state))

    def test_settings_roundtrip(self):
        self.configure()
        with patch.object(P.Path, 'home', return_value=self.home):
            self.assertEqual(P.load_settings(str(self.state)), (self.wine, self.state, [self.media]))

    def test_unmounted_or_replaced_media_is_rejected(self):
        self.configure()
        self.mount_mock.return_value = {'target': '/', 'filesystem': 'fixture', 'root': '/', 'identity': 'different'}
        with patch.object(P.Path, 'home', return_value=self.home), self.assertRaisesRegex(ValueError, 'missing or changed'):
            P.load_settings(str(self.state))

    def test_synthetic_command_is_offline_without_host_home_or_media(self):
        args = P.command(self.wine, self.state, [self.media], 'synthetic')
        self.assertIn('--unshare-all', args)
        self.assertNotIn('--share-net', args)
        self.assertNotIn('--die-with-parent', args)
        self.assertIn('--clearenv', args)
        self.assertEqual(args[args.index('--cap-drop')+1], 'ALL')
        self.assertEqual(args[args.index('--sync-fd')+1], '3')
        self.assertNotIn(str(self.media), args)
        self.assertNotIn(str(self.home), args)
        self.assertNotIn(str(self.state), args)
        self.assertIn(str(self.state/'prefix'), args)
        self.assertIn(str(self.state/'home'), args)
        self.assertNotIn('DISPLAY', args)
        self.assertEqual(args[-6:], ['--remount-ro', '/', '--', '/bin/bash', '/session.sh', 'synthetic'])
        self.assertEqual(args[-4:], ['--', '/bin/bash', '/session.sh', 'synthetic'])

    def test_missing_helper_blocks_run(self):
        (self.package/'build/psp-worker-helper.dll').unlink()
        with self.assertRaisesRegex(ValueError, 'Build the helper'):
            P.command(self.wine, self.state, [], 'run')

    def test_wrong_application_path_blocks_run(self):
        with self.assertRaisesRegex(ValueError, 'not installed'):
            P.command(self.wine, self.state, [], 'run')

    def test_remote_display_blocked(self):
        with self.assertRaisesRegex(ValueError, 'local X11'):
            P.command(self.wine, self.state, [], 'initialize', display='remote.example.invalid:0')

    def test_unknown_mode_blocked(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            P.command(self.wine, self.state, [], 'other')


if __name__ == '__main__':
    unittest.main()
