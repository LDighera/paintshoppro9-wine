# Package checks

The source Makefile builds the startup helper, bootstrap and synthetic test
fixtures with 32-bit MinGW-w64. The five build outputs are created locally.
A synthetic run in a fresh offline Wine 11.14 prefix checked the unload
condition, intentional helper rejection, debugger detachment and normal exit.
A separate check verified the session lock lifetime.

The 20 launcher and frontend tests cover private settings, filesystem checks
and desktop entry parsing. Run them with the system Python as described in
[validation](VALIDATION.md). The same page records the application tests for
the copied-application route, including saving an edited PNG to mounted SMB
storage. See [dependencies](DEPENDENCIES.md) for the build and runtime inputs.
