"""Private-file protection and desktop parser checks; no application launch."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import menu
import create_desktop


class FrontendTests(unittest.TestCase):
    def test_existing_symlink_and_hardlink_cannot_clobber_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root/'original'
            original.write_bytes(b'unchanged')
            symlink = root/'symlink'
            symlink.symlink_to(original)
            hardlink = root/'hardlink'
            os.link(original, hardlink)
            for candidate in (symlink, hardlink):
                with self.assertRaises((OSError, ValueError)):
                    menu.private_fd(candidate)
                self.assertEqual(original.read_bytes(), b'unchanged')

    def test_fifo_does_not_wait_for_a_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            fifo = Path(tmp)/'fifo'
            os.mkfifo(fifo)
            with self.assertRaises((OSError, ValueError)):
                menu.private_fd(fifo)

    def test_opening_regular_log_does_not_truncate_before_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp)/'log'
            log.write_bytes(b'unchanged')
            fd = menu.private_fd(log)
            os.close(fd)
            self.assertEqual(log.read_bytes(), b'unchanged')
            self.assertEqual(log.stat().st_mode & 0o777, 0o600)

    def test_exec_roundtrip_through_desktop_and_argument_parsers(self):
        try:
            from gi.repository import GLib
        except ImportError:
            self.skipTest('Use Debian /usr/bin/python3 with python3-gi for desktop parser validation.')
        values = ['/usr/bin/python3', '-B', '/tmp/a b/quote"d\\ollar$`percent%.py', '/tmp/state']
        raw = '[Desktop Entry]\nType=Application\nName=Test\nExec='+ ' '.join(create_desktop.quote(v) for v in values)+'\n'
        keyfile = GLib.KeyFile()
        keyfile.load_from_data(raw, len(raw), GLib.KeyFileFlags.NONE)
        line = keyfile.get_string('Desktop Entry', 'Exec')
        valid, argv = GLib.shell_parse_argv(line)
        self.assertTrue(valid)
        # %% is the literal-percent field code, expanded by the desktop launcher.
        self.assertEqual([v.replace('%%', '%') for v in argv], values)


if __name__ == '__main__':
    unittest.main()
