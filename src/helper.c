#define _WIN32_WINNT 0x0600
#include <windows.h>
#include <wchar.h>

#define READY_MAGIC 0x50535039UL
static PTP_WORK retained;
static LONG ready;

static void CALLBACK warmed(PTP_CALLBACK_INSTANCE i, void *context, PTP_WORK work)
{
    (void)i; (void)work;
    SetEvent((HANDLE)context);
}

__declspec(dllexport) DWORD WINAPI Initialize(void *unused)
{
    WCHAR path[MAX_PATH];
    HANDLE event;
    DWORD length;
    (void)unused;
    length = GetModuleFileNameW(NULL, path, MAX_PATH);
    if (!length || length >= MAX_PATH) return 1;
    if (lstrcmpiW(path, L"C:\\PSP9\\Paint Shop Pro 9.exe") &&
        lstrcmpiW(path, L"Z:\\test\\worker-test.exe")) return 2;
    if (retained) return 3;
    event = CreateEventW(NULL, TRUE, FALSE, NULL);
    if (!event) return 4;
    retained = CreateThreadpoolWork(warmed, event, NULL);
    if (!retained) { CloseHandle(event); return 5; }
    SubmitThreadpoolWork(retained);
    if (WaitForSingleObject(event, 5000) != WAIT_OBJECT_0) return 6;
    WaitForThreadpoolWorkCallbacks(retained, FALSE);
    CloseHandle(event);
    InterlockedExchange(&ready, 1);
    return READY_MAGIC;
}

__declspec(dllexport) DWORD WINAPI HelperReady(void)
{
    return InterlockedCompareExchange(&ready, 0, 0) ? READY_MAGIC : 0;
}

BOOL WINAPI DllMain(HINSTANCE module, DWORD reason, LPVOID reserved)
{
    (void)module; (void)reason; (void)reserved;
    /* No loader-lock waits, thread creation or pool cleanup. Retained object
       lives until process termination; Initialize runs outside DllMain. */
    return TRUE;
}
