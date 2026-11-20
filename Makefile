CC := i686-w64-mingw32-gcc
CFLAGS := -O2 -Wall -Wextra -Werror
DLLFLAGS := -shared -Wl,--kill-at

.PHONY: all
all: build/bootstrap.exe build/psp-worker-helper.dll build/worker-test.exe build/unload-probe.dll build/reject-helper.dll

build:
	mkdir -p build

build/bootstrap.exe: src/bootstrap.c | build
	$(CC) $(CFLAGS) -o $@ $<

build/psp-worker-helper.dll: src/helper.c | build
	$(CC) $(CFLAGS) $(DLLFLAGS) -o $@ $<

build/worker-test.exe: src/worker-test.c src/probe.h | build
	$(CC) $(CFLAGS) -o $@ $<

build/unload-probe.dll: src/unload-probe.c src/probe.h | build
	$(CC) $(CFLAGS) $(DLLFLAGS) -o $@ $<

build/reject-helper.dll: src/reject-helper.c | build
	$(CC) $(CFLAGS) $(DLLFLAGS) -o $@ $<
