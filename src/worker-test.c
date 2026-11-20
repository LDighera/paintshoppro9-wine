#include "probe.h"
#include <stdio.h>
#include <string.h>

static struct probe state;

static DWORD WINAPI complete_probe(void *arg)
{
    struct probe *p = arg;
    p->callback_thread = GetCurrentThreadId();
    InterlockedIncrement(&p->calls);
    SetEvent(p->event); /* Last context access; no reference to the unload DLL. */
    return 0;
}

static DWORD WINAPI warm_worker(void *arg)
{
    SetEvent((HANDLE)arg);
    return 0;
}

static void CALLBACK unused_work(PTP_CALLBACK_INSTANCE i, void *p, PTP_WORK w)
{
    (void)i; (void)p; (void)w;
}

static int accepted(int retain, BOOL queued, DWORD wait, DWORD drained, LONG calls)
{
    return queued && wait == (retain ? WAIT_OBJECT_0 : WAIT_TIMEOUT)
        && drained == WAIT_OBJECT_0 && calls == 1;
}

static int selftest(void)
{
    int ok = 1;
    ok &= accepted(0, TRUE, WAIT_TIMEOUT, WAIT_OBJECT_0, 1);
    ok &= accepted(1, TRUE, WAIT_OBJECT_0, WAIT_OBJECT_0, 1);
    ok &= !accepted(0, TRUE, WAIT_OBJECT_0, WAIT_OBJECT_0, 1);
    ok &= !accepted(1, TRUE, WAIT_TIMEOUT, WAIT_OBJECT_0, 1);
    ok &= !accepted(1, FALSE, WAIT_OBJECT_0, WAIT_OBJECT_0, 1);
    ok &= !accepted(1, TRUE, WAIT_FAILED, WAIT_OBJECT_0, 1);
    ok &= !accepted(1, TRUE, WAIT_OBJECT_0, WAIT_TIMEOUT, 1);
    ok &= !accepted(1, TRUE, WAIT_OBJECT_0, WAIT_OBJECT_0, 0);
    ok &= !accepted(1, TRUE, WAIT_OBJECT_0, WAIT_OBJECT_0, 2);
    /* Demonstrate a failed assertion cannot be erased by later success. */
    {
        int failed_then_passed = 1;
        failed_then_passed &= accepted(1, FALSE, WAIT_OBJECT_0, WAIT_OBJECT_0, 1);
        failed_then_passed &= accepted(1, TRUE, WAIT_OBJECT_0, WAIT_OBJECT_0, 1);
        ok &= !failed_then_passed;
    }
    printf("CLASSIFIER_SELFTEST=%s\n", ok ? "PASS" : "FAIL");
    return ok ? 0 : 2;
}

int main(int argc, char **argv)
{
    HMODULE module;
    FARPROC proc;
    configure_fn configure;
    HANDLE warm;
    PTP_WORK retained = NULL;
    DWORD drained;
    int retain, ok;
    setvbuf(stdout, NULL, _IONBF, 0);
    if (argc == 2 && !strcmp(argv[1], "selftest")) return selftest();
    if (argc != 2 || (strcmp(argv[1], "baseline") && strcmp(argv[1], "retained") && strcmp(argv[1], "injected"))) return 2;
    retain = !strcmp(argv[1], "retained");
    if (!strcmp(argv[1], "injected")) {
        typedef DWORD (WINAPI *ready_fn)(void);
        ready_fn check;
        HMODULE helper = GetModuleHandleW(L"psp-worker-helper.dll");
        FARPROC address = helper ? GetProcAddress(helper, "HelperReady") : NULL;
        memcpy(&check, &address, sizeof(check));
        if (!address || check() != 0x50535039UL || IsDebuggerPresent()) {
            printf("INJECTED_HELPER_OR_DETACH_CHECK_FAILED\n"); return 2;
        }
        printf("INJECTED_HELPER_READY_DEBUGGER_ABSENT=1\n");
    }
    module = LoadLibraryA("Z:\\test\\unload-probe.dll");
    if (!module) { printf("LOAD_FAILED=%lu\n", GetLastError()); return 2; }
    proc = GetProcAddress(module, "ConfigureProbe");
    _Static_assert(sizeof(proc) == sizeof(configure), "function pointer size mismatch");
    memcpy(&configure, &proc, sizeof(configure));
    if (!configure) return 2;
    if (retain) {
        retained = CreateThreadpoolWork(unused_work, NULL, NULL);
        if (!retained) { printf("RETAIN_FAILED=%lu\n", GetLastError()); return 2; }
    }
    warm = CreateEventW(NULL, TRUE, FALSE, NULL);
    state.event = CreateEventW(NULL, TRUE, FALSE, NULL);
    state.callback = complete_probe;
    if (!warm || !state.event) return 2;
    if (!QueueUserWorkItem(warm_worker, warm, 0) || WaitForSingleObject(warm, 5000) != WAIT_OBJECT_0)
        return 2;
    CloseHandle(warm);
    printf("CASE=%s WARMED=1 IDLE_MS=7000\n", argv[1]);
    Sleep(7000); /* Wine11.14 idle-worker timeout is5000ms. */
    configure(&state);
    if (!FreeLibrary(module)) return 2; /* Controlled DLL detach, finite2s wait. */
    drained = WaitForSingleObject(state.event, 5000);
    ok = accepted(retain || !strcmp(argv[1], "injected"), state.queued, state.wait_result, drained, state.calls);
    printf("CASE=%s QUEUED=%d QUEUE_ERROR=%lu WAIT=%lu WAIT_ERROR=%lu ELAPSED_MS=%llu DRAIN=%lu CALLS=%ld DETACH_TID=%lu CALLBACK_TID=%lu RESULT=%s\n",
        argv[1], state.queued, state.queue_error, state.wait_result, state.wait_error,
        (unsigned long long)state.elapsed_ms, drained, state.calls,
        state.detach_thread, state.callback_thread, ok ? "PASS" : "FAIL_OR_INCONCLUSIVE");
    if (drained == WAIT_OBJECT_0) CloseHandle(state.event);
    if (retained) CloseThreadpoolWork(retained); /* No callbacks submitted to it. */
    /* On drain failure process exit, not DLL unmapping, owns callback/context. */
    return ok ? 0 : 1;
}
