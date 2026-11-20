# Validation

## 1. Automated checks

From the package directory, run the following in a Linux terminal:

> /usr/bin/python3 -B -m unittest discover -s tests

The tests use temporary synthetic settings. They do not launch Wine or PSP.
The desktop parser check needs Debian python3-gi; a skipped check is not a pass.

For the helper runtime, configure a second fresh state with no media selections,
then use the launch command with that state and `--mode synthetic`. This creates
a disposable offline Wine prefix, exercises the baseline unload condition,
rejects a deliberately failing helper before target main, and verifies successful
helper initialization, debugger detachment and normal synthetic child exit.
Expect exit zero and PSP9-SYNTHETIC-PASSED. Use no licensed application prefix.
A timeout, crash or missing final result is a failure, even if earlier lines pass.

## 2. Application acceptance status — November 19

A fresh prefix was initialized by the packaged runner. A separate copy of the
user's PSP9 application folder was verified and placed at C:\PSP9; no old Wine
registry or saved pictures were imported. The user accepted the license agreement,
cancelled file associations and closed optional registration. A generated 640×480
PNG dragged from Dolphin opened normally, was edited, saved under a new name,
closed and reopened with the edit intact. PNG integrity checks passed and the
original fixture remained unchanged.

Closing PSP with the saved image open returned exit 0 and PSP9-NORMAL-EXIT.
No test-runtime process remained and the session lock was available. This is
portable local-image acceptance for the copied-application route, not a fresh
original-installer test. Application-menu invocation, edited-image reopening and normal shutdown also
passed, and the temporary test entry was removed after verified closure.

A generated PNG opened from the mounted SMB share. Direct Save As succeeded
when the share folder was selected and the user entered only a new filename.
The saved PNG decoded at 640 × 480 and its pixels differed from the source.
The user reported sluggish operation in the large share directory. Direct USB
saving remains untested.

The Learning Center reported identical minimum/maximum dimensions of 639×333; resizing
did not persist. Closing only that palette cleared the workspace. No resize fix
or automatic layout adjustment is included in the package.

## 3. Checklist for another installation

1. Initialize a new prefix and supply your PSP9 through one route in SETUP.
   Record whether you used original installer media or a copied application folder.
2. Launch PSP9. Create and save a copied test image, close it and reopen it.
3. In Dolphin select a real path under one of the configured media folders.
   Drag an image onto PSP, edit it and save under a new filename.
4. Close and reopen that saved image; verify the edit. Repeat with an already
   mounted writable share or USB folder if configured. Confirm the actual output
   is on the intended filesystem.
5. Close PSP normally, including once with an image open. Confirm the launcher
   exits normally and a later launch succeeds without a stale lock.
6. Create the optional menu entry. Verify no terminal or password prompt appears
   and that its image workflow and close behavior are unchanged.

Use your own licensed application and registration information.
