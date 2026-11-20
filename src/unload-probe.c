#include "probe.h"

/* Callback and context belong to the EXE and outlive this DLL. */
static struct probe *configured;

__declspec(dllexport) void WINAPI ConfigureProbe(struct probe *p)
{
    configured = p;
}

BOOL WINAPI DllMain(HINSTANCE module, DWORD reason, LPVOID reserved)
{
    (void)module;
    if (reason == DLL_PROCESS_DETACH && reserved == NULL && configured) {
        struct probe *p = configured;
        ULONGLONG started = GetTickCount64();
        p->detach_thread = GetCurrentThreadId();
        p->queued = QueueUserWorkItem(p->callback, p, WT_EXECUTEDEFAULT);
        p->queue_error = p->queued ? 0 : GetLastError();
        p->wait_result = p->queued ? WaitForSingleObject(p->event, 2000) : WAIT_FAILED;
        p->wait_error = p->wait_result == WAIT_FAILED ? GetLastError() : 0;
        p->elapsed_ms = GetTickCount64() - started;
    }
    return TRUE;
}
