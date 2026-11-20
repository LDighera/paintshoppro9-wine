# Paint Shop Pro 9: observed behavior

## 1. Accepted desktop workflows

On the configured Debian 12 KDE/X11 host with private Wine 11.14:

- Create, edit, save and reopen a PSP image.
- Close normally, including with an image open, using the startup helper.
- Drag an image from Dolphin through an accessible filesystem path, edit it,
  save it, close the image and reopen it.
- Launch from the desktop menu without a terminal or password prompt.
- Use separately supplied Arial fonts; some font-list interactions were delayed.

These are results of the configured desktop installation. The public source
archive is not a tested replacement for that installation's launcher or sandbox.

## 2. Why a helper exists

Investigation associated the shutdown hang with work submitted during DLL unload
after the Wine thread pool's idle workers had gone away. The local workaround
creates and retains one thread-pool work object before PSP starts its main code.
Its initialization runs outside DllMain. The object deliberately lives until
process termination; this is a bounded compatibility workaround, not a general
fix for Wine thread pools or all PSP hangs.

The bootstrap starts a new, fixed application target, initializes the helper,
detaches its debugger connection and resumes the application. It never attaches
to an arbitrary existing process. Startup failure can terminate the child it
just created. It does not change the application executable on disk.

## 3. Prior validation and remaining work

The original synthetic run reproduced the baseline unload timeout, confirmed
that an intentionally rejected helper prevented entry to the target, and verified
that the injected helper was ready with the debugger detached. The injected
unload completed and the child exited normally. Real PSP9 edit/save/reopen and
normal-exit checks subsequently passed.

The source package preserves those components. Its packaging-time compile check
is separate from the prior runtime evidence. No fresh GUI installation, other
Wine version, Wayland session, all-format test or PSP8 qualification is claimed.
Registration and trial restrictions must be resolved through legitimate licensing;
the helper does not address them.
