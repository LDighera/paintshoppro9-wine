# Building and evaluating the PSP9 helper

## 1. Build only

Requirements: GNU make and a MinGW-w64 compiler targeting 32-bit Windows, exposed
as `i686-w64-mingw32-gcc`. The Makefile uses warnings as errors and exports the
DLL entry points without stdcall name suffixes.

From the root of this extracted repository, the following is the Linux terminal
command to compile the sources. It does not start Wine or install files:

> make

Build products go into `build/`. The package contains no prebuilt executable.
Do not run the unload test fixtures in an established application prefix: they
deliberately reproduce a blocking DLL-unload pattern and a failed helper load.

## 2. Fixed runtime paths

The preserved bootstrap is specific to the tested layout:

| Windows path | Meaning |
| --- | --- |
| `C:\PSP9\Paint Shop Pro 9.exe` | The licensed PSP9 executable in the test prefix |
| `Z:\test\psp-worker-helper.dll` | Built helper, exposed as `/test` in the test environment |
| `Z:\test\bootstrap.exe` | Built bootstrap |
| `Z:\test\worker-test.exe` | Synthetic target, not PSP |
| `Z:\test\unload-probe.dll` | Synthetic unload fixture |
| `Z:\test\reject-helper.dll` | Deliberately rejected DLL fixture |

These are runtime path requirements, not instructions to create a global `/test`
directory or move an existing application. The portable psp9.py runner exposes the build-products directory read-only at
/test and supplies its private prefix. Follow SETUP.md; simply running the
bootstrap in an unrelated prefix will not provide those mappings.

## 3. Evaluation sequence

The bootstrap accepts `--synthetic`, `--reject-helper` or `--psp9`. The worker
fixture accepts `selftest`, `baseline`, `retained` or `injected`. These are interface
descriptions, not a recommendation to run the application before preparing its
isolated paths and licensed installation.

In a disposable environment, first verify the classifier and baseline, then
helper rejection, then successful injected execution with debugger detachment.
The rejection case must return a failure and must not enter the target's main
code. A timeout or missing exit record is not success. Finally test a copied
image through edit/save/reopen and normal application close. Preserve an existing
working prefix until that sequence succeeds.

The bootstrap may terminate only the child it created if initialization fails.
It cannot safely be used as a generic attach-to-running-PSP repair tool.
