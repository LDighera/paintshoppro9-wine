# Linux and network file access

## 1. Prefer an accessible filesystem path

A file visible in Dolphin is not necessarily visible inside a Wine sandbox.
`smb://` and `ftp://` URLs, search-result URLs and Linux filesystem paths are
different kinds of location. The tested drag-and-drop route uses a real file
path from a share already mounted on Linux and exposed to PSP.

In a conventional Wine prefix, `Z:` often maps to the Linux root. In a sandbox,
it maps only to the filesystem visible inside that sandbox. Host `/tmp` may be
replaced by a private temporary directory. Copying an image to host `/tmp` does
not guarantee PSP can open it. Inspect the prefix's drive mappings and launcher
mounts before diagnosing a damaged image.

## 2. Practical workflow

1. In Dolphin, open the mounted share or a local pictures folder. Use the location
   bar for a directory path; Dolphin's Find field searches rather than navigates.
2. Confirm that the PSP environment can read that same file path. For saving,
   the destination also needs write access inside the application environment.
3. Drag a copied test image onto PSP and make a small edit. In **Save As**,
   select the destination folder, then enter only the new filename in **File name**.
   In the SMB test, pasting a drive-qualified path there caused PSP to append
   it to the selected folder and report that the folder was read-only.
4. Close the image and reopen the saved copy before editing important originals.

A network folder containing thousands of images can stall PSP's older file
picker while it enumerates files. Choosing the file in Dolphin avoids that
particular browsing step, though network reads can still take time. If PSP
reports a writable share as read-only when saving, use Save As in a local
folder and copy the saved image to the share in Dolphin.

The package does not create mounts, store network credentials or install broad
permissions. Those are local configuration choices. Direct remote-URL drops
are not qualified by this source package.
