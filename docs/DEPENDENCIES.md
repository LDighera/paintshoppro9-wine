# 1. Source and application boundaries

Project launcher/helper source and documentation use the included MIT license.
Wine and its upstream fix retain their own terms. Paint Shop Pro, its libraries,
registration data and proprietary fonts are user-supplied and not redistributed.
The helper is a private compatibility workaround; it does not patch PSP on disk
or bypass license checks. See [HELPER.md](HELPER.md) for its fixed targets.

# 2. Recorded inputs

| Input | Version or identity |
| --- | --- |
| PSP | 9.00, executable version 9.0.0.0 / 9.000 Release, 32-bit; not PSP8 or a claim about 9.01 |
| Wine | 11.14, source commit `1012f3d99507b80d4869eabf0853567660a7ecbb` |
| Upstream input fix | `a1bae27f21b53fa3ac6be6b08f4cbfb441360ade` |
| Corrected Wine input.c | Git blob `71219aed5fec18e9c30d5f0d098742814b7248b6` |
| Wine compiler | Debian LLVM/Clang 14, dual-architecture WoW64 |
| Helper compiler | `i686-w64-mingw32-gcc`, 32-bit outputs; warnings treated as errors |
| Desktop | Debian 12 amd64, KDE/X11, ordinary Linux user |

The build script verifies the Wine source/fix hashes. These are the recorded
working inputs, not evidence that newer Wine releases need the same fix.
The exact recipe has not been tested end to end on a clean Debian machine.

# 3. Dependencies

Wine build packages are listed in [debian12-packages.txt](../debian/debian12-packages.txt).
The helper also needs `make` and `gcc-mingw-w64-i686`. Runtime tools are Python 3,
Bubblewrap, Bash and coreutils, util-linux (`findmnt`), and Wine's libraries.
The optional desktop frontend needs `kdialog` and `desktop-file-utils`.
`python3-gi` supplies GLib/Gio for the desktop-parser test, not the PSP runtime.
No pip packages are required by the launcher. The user must be allowed to create
unprivileged namespaces and have a working local X11 display/authorization file.

The runner gives PSP no external network interface, exposes selected writable
picture folders, and keeps its prefix separate. It shares X11 with your desktop;
this is not a hostile-program security guarantee. Fonts come from the host font
configuration or your own legitimately supplied installation. No proprietary
font package is bundled; unavailable fonts may be substituted.

# 4. Evidence and remaining qualification

Helper compilation, synthetic shutdown lifecycle, namespace lock lifetime and
20 runner/frontend tests passed during November 13 preparation. Actual PSP9
workflows passed in the original deployment. They do not establish fresh portable
installation or acceptance of this package's different launcher and file access.
November19 additionally qualified local PNG drag/drop/edit/save/reopen and clean
exit in the new package using the copied-application route. See
[VALIDATION.md](VALIDATION.md) for details and remaining checks.
