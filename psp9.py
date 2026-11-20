#!/usr/bin/env python3
"""Portable PSP9 setup/launch. Private settings stay outside this source tree."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parent
PROGRAM = Path('prefix/drive_c/PSP9/Paint Shop Pro 9.exe')


def need(condition, message):
    if not condition:
        raise ValueError(message)


def clean_path(value, *, exists=True):
    p = Path(value).expanduser()
    need(p.is_absolute() and not any(ord(c) < 32 for c in str(p)), 'Use an absolute path without control characters.')
    need(p.resolve() == p, 'Use the real path, without symlinks or .. components.')
    if exists:
        need(p.exists(), 'A required path is missing.')
    return p


def overlaps(a, b):
    return a == b or a in b.parents or b in a.parents


def user_folder(folder, home):
    need(folder != home and folder not in home.parents, 'Select individual folders, not the entire home or a parent.')
    if home in folder.parents:
        need(not folder.relative_to(home).parts[0].startswith('.'), 'Do not expose hidden home settings directories.')


def mount_identity(folder):
    result = subprocess.run(['/usr/bin/findmnt', '--json', '--target', str(folder),
                             '--output', 'TARGET,SOURCE,FSTYPE,FSROOT,UUID'],
                            capture_output=True, text=True, timeout=10)
    need(result.returncode == 0, 'Cannot identify a media filesystem.')
    rows = json.loads(result.stdout)['filesystems']
    need(len(rows) == 1, 'Ambiguous media filesystem.')
    row = rows[0]
    need(all(isinstance(row.get(k), str) and row[k] for k in ('target', 'source', 'fstype', 'fsroot')),
         'Incomplete media filesystem identity.')
    # UUID survives device-number changes; network filesystems use their source.
    return {'target': row['target'], 'filesystem': row['fstype'], 'root': row['fsroot'],
            'identity': 'uuid:'+row['uuid'] if row.get('uuid') else 'source:'+row['source']}


def check_layout(wine, state, media, home):
    need((wine/'bin/wine').is_file() and (wine/'bin/wineserver').is_file(), 'Wine installation is incomplete.')
    need(not overlaps(wine, state) and not overlaps(PACKAGE, state), 'State must be separate from Wine and package source.')
    protected = [Path('/usr'), Path('/etc'), Path('/proc'), Path('/sys'), Path('/dev'),
                 Path('/run'), home/'.ssh', home/'.gnupg', home/'.config', home/'.local',
                 Path('/wine'), Path('/trial'), Path('/test'), Path('/installer'),
                 Path('/session.sh'), Path('/bin'), Path('/sbin'), Path('/lib'), Path('/lib64'),
                 Path('/tmp/.X11-unix'), wine, state, PACKAGE]
    for folder in media:
        need(folder.is_dir(), 'Each media path must be a directory.')
        user_folder(folder, home)
        need(not any(overlaps(folder, p) for p in protected), 'A media folder overlaps protected runtime/settings paths.')
        need(os.access(folder, os.R_OK | os.W_OK | os.X_OK), 'A media folder is not readable and writable.')
    need(len(media) == len(set(media)), 'Duplicate media folders.')
    need(not any(overlaps(a, b) for i, a in enumerate(media) for b in media[i+1:]), 'Media folders must not overlap.')


def ordinary_user():
    need(os.getuid() != 0, 'Run as the ordinary desktop user; do not use sudo.')


def initialize_settings(args):
    ordinary_user()
    state = clean_path(args.state, exists=False)
    wine = clean_path(args.wine)
    media = [clean_path(p) for p in args.media]
    need(not state.exists() and not state.is_symlink(), 'State already exists; nothing was overwritten.')
    need(state.parent.is_dir() and state.parent.stat().st_uid == os.getuid(), 'Choose a state parent owned by the current user.')
    check_layout(wine, state, media, Path.home().resolve())
    mounts = {str(p): mount_identity(p) for p in media}
    state.mkdir(mode=0o700)
    for name in ('home', 'prefix'):
        (state/name).mkdir(mode=0o700)
    data = dict(version=1, wine=str(wine), media=[str(p) for p in media], mounts=mounts)
    with (state/'settings.json').open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')
    (state/'settings.json').chmod(0o600)
    print('Private settings created. No Wine process started. Next: initialize, then install.')


def load_settings(value):
    state = clean_path(value)
    need(state.is_dir() and state.stat().st_uid == os.getuid() and
         stat.S_IMODE(state.stat().st_mode) == 0o700, 'State must be owned by you with mode 0700.')
    path = state/'settings.json'
    need(not path.is_symlink() and path.is_file() and path.stat().st_uid == os.getuid() and
         stat.S_IMODE(path.stat().st_mode) == 0o600, 'Private settings must be a regular owned file with mode 0600.')
    need(path.stat().st_size < 32768, 'Settings file is too large.')
    def unique(pairs):
        result = {}
        for key, item in pairs:
            need(key not in result, 'Duplicate settings key.')
            result[key] = item
        return result
    data = json.loads(path.read_text(), object_pairs_hook=unique)
    need(set(data) == {'version', 'wine', 'media', 'mounts'} and type(data['version']) is int and
         data['version'] == 1 and isinstance(data['wine'], str) and
         isinstance(data['media'], list) and all(isinstance(p, str) for p in data['media']), 'Invalid settings schema.')
    wine = clean_path(data['wine'])
    media = [clean_path(p) for p in data['media']]
    check_layout(wine, state, media, Path.home().resolve())
    need(isinstance(data['mounts'], dict) and set(data['mounts']) == set(data['media']), 'Invalid media mount settings.')
    for folder in media:
        need(mount_identity(folder) == data['mounts'][str(folder)],
             'A media filesystem is missing or changed. Reconnect the expected drive/share before launching.')
    for name in ('home', 'prefix'):
        p = state/name
        need(p.is_dir() and not p.is_symlink() and p.stat().st_uid == os.getuid(), 'Private prefix/home directory is invalid.')
    return wine, state, media


def command(wine, state, media, mode, installer=None, *, display=None, auth=None):
    need(mode in ('initialize', 'install', 'run', 'synthetic'), 'Unsupported launch mode.')
    for tool in ('/usr/bin/bwrap', '/usr/bin/bash'):
        need(os.access(tool, os.X_OK), 'A required system tool is missing.')
    need((PACKAGE/'session.sh').is_file(), 'Session script missing.')
    gui = mode != 'synthetic'
    args = ['/usr/bin/bwrap', '--unshare-all', '--cap-drop', 'ALL', '--new-session',
            '--sync-fd', '3',
            '--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin',
            '--symlink', 'usr/sbin', '/sbin', '--symlink', 'usr/lib', '/lib',
            '--symlink', 'usr/lib64', '/lib64', '--proc', '/proc', '--dev', '/dev',
            '--tmpfs', '/tmp', '--dir', '/run', '--clearenv']
    for p in ('/etc/fonts', '/etc/ld.so.cache', '/etc/passwd', '/etc/group', '/etc/localtime'):
        if Path(p).exists():
            args += ['--ro-bind', p, p]
    args += ['--ro-bind', str(wine), '/wine', '--tmpfs', '/trial',
             '--bind', str(state/'prefix'), '/trial/prefix',
             '--bind', str(state/'home'), '/trial/home',
             '--ro-bind', str(PACKAGE/'session.sh'), '/session.sh']
    if mode in ('run', 'synthetic'):
        needed = ['bootstrap.exe', 'psp-worker-helper.dll']
        if mode == 'synthetic':
            needed += ['worker-test.exe', 'unload-probe.dll', 'reject-helper.dll']
        for name in needed:
            need((PACKAGE/'build'/name).is_file(), 'Build the helper first with make.')
        args += ['--ro-bind', str(PACKAGE/'build'), '/test']
    if mode == 'run':
        need((state/PROGRAM).is_file(), 'PSP9 is not installed at C:\\PSP9\\Paint Shop Pro 9.exe.')
    if gui:
        need(display is not None and re.fullmatch(r':[0-9]+(?:\.[0-9]+)?', display), 'A local X11 DISPLAY is required.')
        socket = Path('/tmp/.X11-unix')/('X'+display[1:].split('.')[0])
        need(socket.exists() and stat.S_ISSOCK(socket.stat().st_mode), 'The X11 display socket is missing.')
        auth = clean_path(auth)
        need(auth.is_file() and os.access(auth, os.R_OK), 'Xauthority is unavailable.')
        args += ['--ro-bind', str(socket), str(socket), '--ro-bind', str(auth), '/run/xauthority',
                 '--setenv', 'DISPLAY', display, '--setenv', 'XAUTHORITY', '/run/xauthority']
        for folder in media:
            args += ['--bind', str(folder), str(folder)]
    if mode == 'install':
        need(installer is not None, 'Supply --installer for install mode.')
        installer = clean_path(installer)
        need(installer.is_file() and installer.suffix.lower() in ('.exe', '.msi'), 'Select the licensed EXE or MSI installer.')
        parent = installer.parent
        user_folder(parent, Path.home().resolve())
        # Reuse media path restrictions, but an installer directory need not
        # be writable. Do not expose controls, system roots or secret folders.
        need(not any(overlaps(parent, p) for p in [wine, state, PACKAGE, Path('/usr'),
             Path('/etc'), Path('/proc'), Path('/sys'), Path('/dev'), Path('/run'),
             Path('/wine'), Path('/trial'), Path('/test'), Path('/installer'),
             Path('/tmp/.X11-unix')]), 'Use a separate extracted-installer directory.')
        # The adjacent CAB/resource files must be visible to the installer too.
        args += ['--ro-bind', str(parent), '/installer']
    user = pwd.getpwuid(os.getuid()).pw_name
    for key, value in {'PATH': '/wine/bin:/usr/bin:/bin', 'HOME': '/trial/home',
                       'USER': user, 'LOGNAME': user, 'LANG': 'C.UTF-8',
                       'WINEPREFIX': '/trial/prefix', 'WINEARCH': 'wow64',
                       'WINESERVER': '/wine/bin/wineserver', 'WINEDEBUG': '-all',
                       'WINEDLLOVERRIDES': 'mscoree=d;mshtml=d;winemenubuilder.exe=d'}.items():
        args += ['--setenv', key, value]
    args += ['--chdir', '/trial', '--remount-ro', '/', '--', '/bin/bash', '/session.sh', mode]
    if mode == 'install':
        args.append('Z:\\installer\\'+installer.name)
    return args


def launch(args):
    ordinary_user()
    wine, state, media = load_settings(args.state)
    need(args.mode != 'synthetic' or not (state/PROGRAM).exists(), 'Synthetic tests require a separate prefix without PSP.')
    argv = command(wine, state, media, args.mode, args.installer,
                   display=os.environ.get('DISPLAY'),
                   auth=os.environ.get('XAUTHORITY', str(Path.home()/'.Xauthority')))
    if args.plan:
        print(json.dumps(argv, indent=2))
        return
    fd = os.open(state/'session.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    info = os.fstat(fd)
    need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid(), 'Invalid session lock.')
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise ValueError('This PSP environment is already running; close it normally first.')
    # Bubblewrap keeps its sync descriptor open for the sandbox lifetime.
    # Only this standalone CLI owns these descriptors.
    if fd != 3:
        os.dup2(fd, 3, inheritable=True)
        os.close(fd)
    os.set_inheritable(3, True)
    os.execv(argv[0], argv)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='action', required=True)
    init = subs.add_parser('configure', help='Create private settings only, without launching Wine.')
    init.add_argument('--wine', required=True)
    init.add_argument('--state', required=True)
    init.add_argument('--media', action='append', default=[])
    run = subs.add_parser('launch')
    run.add_argument('--state', required=True)
    run.add_argument('--mode', choices=('initialize', 'install', 'run', 'synthetic'), default='run')
    run.add_argument('--installer')
    run.add_argument('--plan', action='store_true', help='Print argv only; paths in this output are private.')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.action == 'configure':
            initialize_settings(args)
        else:
            launch(args)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print('PSP9 stopped: '+str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
