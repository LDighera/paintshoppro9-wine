# Paint Shop Pro 9 under Wine — November 20, 2026 release candidate

This source package runs a separately supplied, licensed copy of PSP 9.00 on
Debian 12 amd64 with KDE/X11. It includes an offline launcher, a startup helper
for clean shutdown, a Wine 11.14 build recipe and an optional applications-menu
entry. Start with the [setup instructions](docs/SETUP.md).

The copied-application route passed menu launch, Dolphin drag-and-drop, local PNG
editing, saving, reopening and normal shutdown. An edited PNG saved directly to a
mounted SMB folder also passed integrity and pixel checks. The Save As dialog
was sluggish in a folder containing thousands of files. Select the destination
folder and type only the filename. See [file access](docs/FILE_ACCESS.md).

The original EXE/MSI installer route, direct USB saves and a full build on a
clean Debian installation remain untested. Users supply their own application
and license.
