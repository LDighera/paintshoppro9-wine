# Paint Shop Pro 9 under Wine

This project supplies the source and setup workflow for a private, offline PSP9
Wine environment on Debian 12 amd64 with KDE/X11. The startup helper addresses
an observed shutdown hang without modifying the original PSP executable.
Use your own licensed PSP9 installer or complete application folder. PSP8, registration bypasses, application
binaries and proprietary fonts are outside this package.

**Tested on Debian 12 with KDE/X11, Wine 11.14 and PSP 9.00.** Using a copy
of a licensed PSP application folder in a fresh prefix, we launched PSP from
the applications menu, dragged in a PNG from Dolphin, edited it, saved and
reopened it locally, and closed PSP normally. We also opened a PNG from a
mounted SMB share and saved an edited copy directly to the same folder.
In **Save As**, select the folder and enter only the new filename. Large
network folders can make the dialog very slow.

Installation from original installer media and direct USB saves are untested.

## 1. Start here

1. Read [setup](docs/SETUP.md) for prerequisites, the pinned Wine build, private
   configuration, installation and the optional terminal-free menu entry.
2. Read [file access](docs/FILE_ACCESS.md) before selecting writable folders.
3. Use [validation](docs/VALIDATION.md) with copies of pictures before real work.

[Dependency inventory](docs/DEPENDENCIES.md), [helper details](docs/HELPER.md), [prior experience](docs/EXPERIENCE.md),
[checks](docs/PACKAGE_CHECKS.md) and [release notes](RELEASE_NOTES.md) explain the
implementation and limits. Settings, prefix, registration data and latest log
live outside this source directory. Do not upload them with a bug report.

## 2. What the runner does

The runner uses unprivileged Bubblewrap, a separate Wine 11.14 installation and
one private prefix. It provides no Internet network interface. It exposes only
selected writable media folders at their normal Linux paths, a private temporary
directory and the local X11 display. It creates no host mounts or system service,
changes no other application's prefix and requires no sudo at launch.

The shared X11 connection permits interaction with the desktop; this is not a
security boundary against malicious Windows programs. Selected writable folders
can be changed by PSP. Use trusted licensed software and backups.

A private session lock prevents concurrent use of this prefix. Normal close waits
for its wineserver. A hung wineserver can retain the lock: investigate that
specific session rather than issuing a global wineserver kill or launching again.

## 3. Feedback and credit

Report the PSP/Wine versions, session type, local or mounted file location and
exact failing action. Never send license keys, private settings, images or raw
logs without reviewing their contents. Larry Dighera exercised the applications;
OpenAI Codex performed investigation and helper development. Original project
source/documentation is [MIT licensed](LICENSE). Wine and PSP have separate terms.
