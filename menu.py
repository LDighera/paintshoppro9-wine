#!/usr/bin/env python3
"""Terminal-free desktop frontend; no automatic retry or forced application stop."""
import fcntl
import os
from pathlib import Path
import stat
import subprocess
import sys
import psp9


def notice(text):
    if Path('/usr/bin/kdialog').is_file():
        subprocess.run(['/usr/bin/kdialog', '--title', 'Paint Shop Pro 9', '--error', text], check=False)
    else:
        print(text, file=sys.stderr)


def private_fd(path):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
        os.close(fd)
        raise ValueError('Invalid private frontend file.')
    os.fchmod(fd, 0o600)
    return fd


def main():
    os.umask(0o077)
    lock = None
    try:
        psp9.ordinary_user()
        if len(sys.argv) != 2:
            raise ValueError('The menu entry requires its private state directory.')
        _, state, _ = psp9.load_settings(sys.argv[1])
        lock = private_fd(state/'menu.lock')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('PSP9 is already starting or running from this menu.')
        log = private_fd(state/'latest.log')
        os.ftruncate(log, 0)
        with os.fdopen(log, 'wb', buffering=0) as stream:
            child = subprocess.Popen(['/usr/bin/python3', '-B', str(psp9.PACKAGE/'psp9.py'),
                                      'launch', '--state', str(state)],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            while True:
                block = child.stdout.read1(4096)
                if not block:
                    break
                if stream.tell()+len(block) > 262144:
                    stream.seek(0)
                    stream.truncate()
                    stream.write(b'[Earlier frontend output omitted.]\n')
                stream.write(block)
            code = child.wait()
        if code:
            notice('PSP9 did not complete normally. Do not launch another copy while it is open.\n'
                   'Private details: '+str(state/'latest.log'))
        return code
    except (ValueError, OSError) as exc:
        notice('PSP9 could not start: '+str(exc))
        return 2
    finally:
        if lock is not None:
            os.close(lock)


if __name__ == '__main__':
    raise SystemExit(main())
