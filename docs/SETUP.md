# 1. What this package supplies

These instructions target Paint Shop Pro **9.00**, Debian 12 amd64 and KDE/X11.
They supply a separate Wine environment, an offline launcher, a shutdown helper
and optional application-menu entry. No PSP application, registration information,
proprietary fonts or pictures are included. Use your own legitimately obtained
PSP files and satisfy their license requirements. PSP8 is outside this release.

A **Wine installation** contains the Linux programs that run PSP. A **prefix** is
Wine's private Windows environment. This package keeps that prefix and PSP's
settings in a separate **state directory**. Your pictures remain in whichever
existing folders you choose to expose. You do not need to reorganize them.

**Tested route (section 5B).** A licensed PSP9 application folder copied to a
fresh prefix passed local PNG editing, save/reopen, menu launch and clean exit.
PSP also opened a PNG from a mounted SMB folder and saved an edited copy there.
See [file access](FILE_ACCESS.md) for the Save As filename procedure.

Section 5A covers original EXE/MSI media. That installer route and running the
full Wine build recipe on a clean Debian host remain unverified.

# 2. Prerequisites and helper build

Use your ordinary Linux desktop account, not root. The runner refuses root.
Rootless Bubblewrap namespaces must be permitted; do not bypass a failure by
running PSP with sudo. Keep the original working PSP installation unchanged.

Extract this package into a new, permanent directory. Open a terminal **in that
package directory**, which contains `psp9.py`, `Makefile` and the `debian` folder.
All commands below run there, unless another location is explicitly stated.

As the administrator, review and install the Debian dependencies. Copy each
quoted command separately into that Linux terminal. Review apt's proposed changes
and stop on signature errors, unexpected removals or release upgrades.

> sudo apt-get update

> sudo xargs -r -a debian/debian12-packages.txt apt-get install --no-install-recommends

> sudo apt-get install --no-install-recommends make gcc-mingw-w64-i686 python3 bubblewrap util-linux kdialog desktop-file-utils python3-gi

Only those package-install commands use sudo. Compile the helper as your ordinary
user, from the same package directory:

> make

Expected: five outputs in `build/`, including `bootstrap.exe` and
`psp-worker-helper.dll`, and no compiler error. Stop on failure. Build products
are local; do not add them, your PSP files, or private settings to the source ZIP.
The source package must remain readable at this location for its launcher to work.
See [dependencies](DEPENDENCIES.md) for the version and licensing boundaries.

# 3. Build a separate Wine installation

The recipe uses Wine 11.14 and verifies its pinned release commit, upstream input
fix and resulting changed-file hash. It downloads public source and builds under
a new directory; it does not replace system Wine. Allow several GiB for the build
and monitor free space. A new application prefix requires additional space.

This command selects `psp9-wine-build` in your home. It must not already exist.
Copy into the Linux terminal in the package directory, without sudo:

> bash debian/build-wine-debian12.sh "$HOME/psp9-wine-build"

Expected: `Wine build complete` and the `wine-install` path. Stop on a compiler
error or missing X11/font/TLS support; retain the logs. A final version string
alone does not establish that the build succeeded. Do not rerun over a partial
build directory. The script supplies no automatic repair or retry.

The commands below assume this build location. If you already have a verified
build matching the recorded source/fix, use its actual `wine-install` path in
section 4 instead. Do not substitute an unrelated system Wine installation.

# 4. Create private state and select your picture folders

This example chooses a NEW private directory `$HOME/psp9-portable-state` and
exposes your existing Pictures directory read/write. Pictures must already exist.
Copy into the same terminal as your ordinary desktop user:

> python3 psp9.py configure --wine "$HOME/psp9-wine-build/wine-install" --state "$HOME/psp9-portable-state" --media "$HOME/Pictures"

Expected: `Private settings created. No Wine process started.` This creates
`settings.json`, `prefix/` and `home/` only inside the new state directory.
It does not launch PSP or copy your pictures. Existing state directories are
refused. Keep state outside this package and the Wine tree, under a parent you own.

Before running that command, you may replace the Pictures path or add another
`--media` argument for an existing mounted NAS/USB folder. Each selected folder
is writable from PSP. Use its actual absolute Linux path, not an `smb://` or
`ftp://` URL. Omit `--media` if you want no external picture-folder access.
Whole homes, hidden home settings, system folders, symlinks and overlapping
selections are refused. Do not select a parent containing your state or Wine tree.

Mount shares/drives through Linux first. This package neither mounts devices nor
stores share passwords. It records the selected filesystem identity and refuses
launch if the mount disappears or changes. Do not edit identity checks to silence
that warning. Restore the intended mount, or review a separate new configuration.
See [file access](FILE_ACCESS.md) before choosing a large network directory.

# 5. Initialize, then supply PSP by one of the following routes

The following command starts Wine only in the new, network-isolated prefix.
Use the same ordinary-user X11 terminal:

> python3 psp9.py launch --state "$HOME/psp9-portable-state" --mode initialize

Expected: `PSP9-PREFIX-INITIALIZED`, then a returned terminal prompt. Stop if it
fails or hangs. The runner uses your current DISPLAY and XAUTHORITY; it does not
weaken X11 authorization. Do not initialize an existing working PSP prefix.

## 5A. If you have the original installer

Keep the EXE or MSI and any adjacent CAB/resource files together in a dedicated
installer directory outside this package/state/Wine tree. The entire installer
directory is exposed read-only; keep unrelated private files elsewhere. In the
command below, replace the last quoted path with your actual installer path.
It is a template, not a filename supplied by this package:

> python3 psp9.py launch --state "$HOME/psp9-portable-state" --mode install --installer "/absolute/path/to/your/PSP9-installer.exe"

In the installer, choose **C:\PSP9** as the application destination. Make your
own license/registration decisions. No key, trial reset or registration bypass
is supplied. When the installer closes, the terminal says
`PSP9-INSTALLER-CLOSED: check installation path before running.` This message
means the installer exited, not proof that PSP installed correctly.

Verify the file `prefix/drive_c/PSP9/Paint Shop Pro 9.exe` under your chosen state
directory. Stop if missing. An installer that requires writing beside itself or
online activation is not supported by this route as written. Do not expose an
entire home directory or enable networking as an undocumented workaround.

## 5B. If you have your own already installed PSP9 application folder

This matches the source type used for our original working installation. It is
not equivalent to a fresh installer test or proof that every installed copy is
portable. Registry-dependent features or licensing may still require installation.

1. Close the source PSP normally. Keep its application folder and settings intact.
2. With the new Wine initialization complete and no test PSP open, use Dolphin
   to copy the **complete application folder** into the new state directory's
   `prefix/drive_c`, naming the copied folder **PSP9**. The destination must not
   already contain a PSP9 installation; do not merge or overwrite one.
3. Check that `prefix/drive_c/PSP9/Paint Shop Pro 9.exe` exists directly inside
   that folder, with its companion DLLs/resources. Do not copy just the EXE,
   nest a second application folder underneath PSP9, or use a symlink to the
   original. Verify the copy with your copy tool or file checksums.
4. Do not import the old Wine registry, another person's registration data,
   unrelated Windows files or the working installation's entire prefix.
   Keep any license data in your own private copy; none belongs in this package.
5. If launch reports missing components or licensing, stop and preserve the
   message. The helper fixes an observed shutdown problem, not installation or
   registration problems.

# 6. Open and validate PSP

From the package directory, as your desktop user, copy this into the terminal:

> python3 psp9.py launch --state "$HOME/psp9-portable-state"

Expected: PSP9 opens. Keep the terminal open while working. The helper is mapped
internally at `/test`; do not create a host `/test` directory. Test with disposable
pictures using [the validation checklist](VALIDATION.md), then close PSP through
its own File → Exit command. Expect `PSP9-NORMAL-EXIT` and a returned prompt.
A disappearing window alone is not proof that the background Wine process exited.

If registration/file-association dialogs appear, make your own license decisions
and decline optional associations for the initial test. Stop on an unexpected
error rather than importing more DLLs or restarting repeatedly. Selected media
folders remain writable: always save test edits under a new name.

# 7. Optional terminal-free menu entry

After the image workflow and normal close pass, create the menu entry. Ensure
`$HOME/.local/share/applications` exists (create it with Dolphin if needed).
The following command writes a new file only and refuses an existing one:

> python3 create_desktop.py --state "$HOME/psp9-portable-state" --output "$HOME/.local/share/applications/psp9-portable.desktop"

Expected: `Created desktop entry. Existing menu items and favorites were not changed.`
Choose the new **Paint Shop Pro 9** entry in Applications. If another entry has the
same name, inspect launcher properties: the new one refers to this package's
`menu.py` and your `psp9-portable-state` directory. Do not replace Favorites until
this entry passes validation. No terminal or password prompt should appear.

The frontend writes `latest.log` in private state, capped at 256 KiB. A later
launch replaces that log. Normal completion includes `PSP9-NORMAL-EXIT`; on failure,
preserve the current log before another launch. Review its content before sharing.

# 8. Stop, backup and return to the old installation

Close PSP normally and wait for its Wine session to finish. If it hangs, preserve
the log and identify this specific prefix's processes before any recovery action.
There is no automatic force-close. Never issue a global wineserver kill; other
Windows applications may be using different prefixes.

With PSP closed, back up the entire private state directory and separately stored
pictures. Neither a state backup nor an application-folder copy contains pictures
saved elsewhere. To stop using the test setup, retain those files, close it normally
and use your unchanged original launcher. The recipe replaced no system Wine,
service or host mount. Do not remove state while the application is running.
