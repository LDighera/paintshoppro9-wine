#ifndef PROBE_H
#define PROBE_H
#define _WIN32_WINNT 0x0600
#include <windows.h>

struct probe {
    LPTHREAD_START_ROUTINE callback;
    HANDLE event;
    volatile LONG calls;
    DWORD callback_thread;
    DWORD detach_thread;
    BOOL queued;
    DWORD queue_error;
    DWORD wait_result;
    DWORD wait_error;
    ULONGLONG elapsed_ms;
};
typedef void (WINAPI *configure_fn)(struct probe *);
#endif
