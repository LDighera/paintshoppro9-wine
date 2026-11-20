#!/usr/bin/env python3
"""Write one new desktop entry; never replace an existing entry or run PSP."""
import argparse
from pathlib import Path
import os
import subprocess
import psp9


def quote(value):
    # Desktop Exec uses its own quoting rules, not shell single quotes.
    psp9.need(not any(ord(c) < 32 for c in value), 'Invalid desktop entry path.')
    value = value.replace('%', '%%')
    for character in ('\\', '"', '`', '$'):
        value = value.replace(character, '\\'+character)
    # The desktop key-value parser consumes one escaping layer before Exec
    # tokenization. Preserve the command-line escapes through that first layer.
    return ('"'+value+'"').replace('\\', '\\\\')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    psp9.ordinary_user()
    _, state, _ = psp9.load_settings(args.state)
    output = psp9.clean_path(args.output, exists=False)
    psp9.need(output.suffix == '.desktop' and output.parent.is_dir(), 'Choose a .desktop file in an existing directory.')
    psp9.need(Path('/usr/bin/kdialog').is_file(), 'Install kdialog before creating the terminal-free entry.')
    psp9.need(Path('/usr/bin/desktop-file-validate').is_file(), 'Install desktop-file-utils first.')
    text = ('[Desktop Entry]\nType=Application\nName=Paint Shop Pro 9\n'
            'Comment=Private offline Wine environment\nTerminal=false\n'
            'Icon=applications-graphics\nCategories=Graphics;RasterGraphics;\nExec='+
            ' '.join(quote(s) for s in ['/usr/bin/python3', '-B', str(psp9.PACKAGE/'menu.py'), str(state)])+'\n')
    os.umask(0o077)
    with output.open('x') as stream:
        stream.write(text)
    result = subprocess.run(['/usr/bin/desktop-file-validate', str(output)])
    psp9.need(result.returncode == 0, 'Desktop validation failed; do not activate the new entry.')
    print('Created desktop entry. Existing menu items and favorites were not changed.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        raise SystemExit('Desktop entry stopped: '+str(exc))
