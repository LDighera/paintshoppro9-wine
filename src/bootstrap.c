#define _WIN32_WINNT 0x0600
#include <windows.h>
#include <tlhelp32.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

#define READY_MAGIC 0x50535039UL

/* Translate an exported routine using the owning module's remote base; never
   assume identical DLL addresses in the launcher and its child. */
static uintptr_t remote_loader(HANDLE process, DWORD pid)
{
    FARPROC fn = GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "LoadLibraryW");
    HMODULE owner;
    WCHAR path[MAX_PATH], *name;
    HANDLE snapshot;
    MODULEENTRY32W entry;
    uintptr_t result = 0;
    DWORD length;
    (void)process;
    if (!fn || !GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
          GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCWSTR)(uintptr_t)fn, &owner)) return 0;
    length = GetModuleFileNameW(owner, path, MAX_PATH);
    if (!length || length >= MAX_PATH) return 0;
    name = wcsrchr(path, L'\\');
    name = name ? name + 1 : path;
    snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, pid);
    if (snapshot == INVALID_HANDLE_VALUE) return 0;
    memset(&entry, 0, sizeof(entry)); entry.dwSize = sizeof(entry);
    if (Module32FirstW(snapshot, &entry)) do {
        if (!lstrcmpiW(entry.szModule, name)) {
            result = (uintptr_t)entry.modBaseAddr + (uintptr_t)fn - (uintptr_t)owner;
            break;
        }
    } while (Module32NextW(snapshot, &entry));
    CloseHandle(snapshot);
    return result;
}

int main(int argc, char **argv)
{
    const WCHAR *exe, *dll;
    WCHAR command[256];
    STARTUPINFOW startup = {0};
    PROCESS_INFORMATION child = {0};
    DEBUG_EVENT event = {0};
    HMODULE local_dll = NULL;
    FARPROC initialize;
    uintptr_t initialize_offset, dll_base = 0;
    void *remote_path = NULL;
    HANDLE remote_thread = NULL;
    DWORD remote_tid = 0, status, child_status;
    uintptr_t entry_address = 0;
    SIZE_T written;
    ULONGLONG deadline;
    int stage = 0, pending = 0, attached = 0, suspended = 0;
    int synthetic, reject;
    setvbuf(stdout, NULL, _IONBF, 0);
    if (argc != 2) return 2;
    synthetic = !strcmp(argv[1], "--synthetic");
    reject = !strcmp(argv[1], "--reject-helper");
    if (!synthetic && !reject && strcmp(argv[1], "--psp9")) return 2;
    exe = (synthetic || reject) ? L"Z:\\test\\worker-test.exe" : L"C:\\PSP9\\Paint Shop Pro 9.exe";
    dll = reject ? L"Z:\\test\\reject-helper.dll" : L"Z:\\test\\psp-worker-helper.dll";
    _snwprintf(command, 256, L"\"%ls\"%ls", exe,
               (synthetic || reject) ? L" injected" : L"");
    command[255] = 0;
    local_dll = LoadLibraryExW(dll, NULL, DONT_RESOLVE_DLL_REFERENCES);
    if (!local_dll) { printf("BOOTSTRAP_PREP_FAILED=%lu\n", GetLastError()); return 2; }
    initialize = GetProcAddress(local_dll, "Initialize");
    if (!initialize) { FreeLibrary(local_dll); return 2; }
    initialize_offset = (uintptr_t)initialize - (uintptr_t)local_dll;
    startup.cb = sizeof(startup);
    if (!CreateProcessW(exe, command, NULL, NULL, FALSE, DEBUG_ONLY_THIS_PROCESS,
                        NULL, NULL, &startup, &child)) {
        printf("CREATE_PROCESS_FAILED=%lu\n", GetLastError());
        FreeLibrary(local_dll); return 2;
    }
    attached = 1;
    printf("BOOTSTRAP_CHILD_PID=%lu\n", child.dwProcessId);
    if (!DebugSetProcessKillOnExit(TRUE)) goto fail;
    deadline = GetTickCount64() + 30000;
    while (GetTickCount64() < deadline) {
        status = DBG_CONTINUE;
        if (!WaitForDebugEvent(&event, 250)) {
            if (GetLastError() == ERROR_SEM_TIMEOUT) continue;
            goto fail;
        }
        pending = 1;
        if (event.dwProcessId != child.dwProcessId) goto fail;
        if (event.dwDebugEventCode == CREATE_PROCESS_DEBUG_EVENT) {
            IMAGE_DOS_HEADER dos;
            IMAGE_NT_HEADERS32 nt;
            SIZE_T got;
            uintptr_t base = (uintptr_t)event.u.CreateProcessInfo.lpBaseOfImage;
            if (!ReadProcessMemory(child.hProcess, (void *)base, &dos, sizeof(dos), &got) ||
                got != sizeof(dos) || dos.e_magic != IMAGE_DOS_SIGNATURE ||
                dos.e_lfanew <= 0 || dos.e_lfanew > 0x100000) goto fail;
            if (!ReadProcessMemory(child.hProcess, (void *)(base + dos.e_lfanew),
                    &nt, sizeof(nt), &got) || got != sizeof(nt) ||
                nt.Signature != IMAGE_NT_SIGNATURE || nt.FileHeader.Machine != IMAGE_FILE_MACHINE_I386 ||
                nt.OptionalHeader.Magic != IMAGE_NT_OPTIONAL_HDR32_MAGIC ||
                !nt.OptionalHeader.AddressOfEntryPoint ||
                nt.OptionalHeader.AddressOfEntryPoint >= nt.OptionalHeader.SizeOfImage) goto fail;
            entry_address = base + nt.OptionalHeader.AddressOfEntryPoint;
            if (event.u.CreateProcessInfo.hFile) CloseHandle(event.u.CreateProcessInfo.hFile);
            if (event.u.CreateProcessInfo.hProcess != child.hProcess)
                CloseHandle(event.u.CreateProcessInfo.hProcess);
            if (event.u.CreateProcessInfo.hThread != child.hThread)
                CloseHandle(event.u.CreateProcessInfo.hThread);
        } else if (event.dwDebugEventCode == LOAD_DLL_DEBUG_EVENT) {
            if (event.u.LoadDll.hFile) CloseHandle(event.u.LoadDll.hFile);
        } else if (event.dwDebugEventCode == CREATE_THREAD_DEBUG_EVENT) {
            if (event.u.CreateThread.hThread != child.hThread &&
                event.u.CreateThread.hThread != remote_thread)
                CloseHandle(event.u.CreateThread.hThread);
        } else if (event.dwDebugEventCode == EXCEPTION_DEBUG_EVENT) {
            if (stage == 0 && event.dwThreadId == child.dwThreadId &&
                event.u.Exception.ExceptionRecord.ExceptionCode == EXCEPTION_BREAKPOINT &&
                event.u.Exception.dwFirstChance) {
                CONTEXT context = {0};
                /* Wine's initial loader breakpoint still owns loader lock.
                   Stop at the EXE entry instead, without patching code bytes. */
                context.ContextFlags = CONTEXT_DEBUG_REGISTERS;
                if (!entry_address || !GetThreadContext(child.hThread, &context) ||
                    (context.Dr7 & 0xff)) goto fail;
                context.Dr0 = (DWORD)entry_address;
                context.Dr6 = 0;
                context.Dr7 = 1; /* Local execution breakpoint, length1. */
                if (!SetThreadContext(child.hThread, &context)) goto fail;
                stage = 1;
            } else if (stage == 1 && event.dwThreadId == child.dwThreadId &&
                       event.u.Exception.ExceptionRecord.ExceptionCode == EXCEPTION_SINGLE_STEP) {
                CONTEXT context = {0};
                uintptr_t loader = remote_loader(child.hProcess, child.dwProcessId);
                SIZE_T bytes = (wcslen(dll) + 1) * sizeof(WCHAR);
                context.ContextFlags = CONTEXT_CONTROL | CONTEXT_DEBUG_REGISTERS;
                if (!GetThreadContext(child.hThread, &context) ||
                    context.Eip != entry_address || !(context.Dr6 & 1)) goto fail;
                context.Dr0 = context.Dr6 = context.Dr7 = 0;
                if (!SetThreadContext(child.hThread, &context)) goto fail;
                if (!loader) goto fail;
                if (SuspendThread(child.hThread) != 0) goto fail;
                suspended = 1;
                remote_path = VirtualAllocEx(child.hProcess, NULL, bytes,
                                             MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
                if (!remote_path || !WriteProcessMemory(child.hProcess, remote_path, dll, bytes,
                                                        &written) || written != bytes) goto fail;
                remote_thread = CreateRemoteThread(child.hProcess, NULL, 0,
                    (LPTHREAD_START_ROUTINE)loader, remote_path, 0, &remote_tid);
                if (!remote_thread) goto fail;
                stage = 2;
            } else {
                printf("UNEXPECTED_DEBUG_EXCEPTION=%08lx\n",
                       event.u.Exception.ExceptionRecord.ExceptionCode);
                goto fail;
            }
        } else if (event.dwDebugEventCode == EXIT_PROCESS_DEBUG_EVENT) {
            printf("PREMATURE_CHILD_EXIT=%lu\n", event.u.ExitProcess.dwExitCode);
            goto fail;
        } else if (event.dwDebugEventCode == EXIT_THREAD_DEBUG_EVENT &&
                   event.dwThreadId == remote_tid) {
            DWORD code = event.u.ExitThread.dwExitCode;
            CloseHandle(remote_thread); remote_thread = NULL;
            if (stage == 2) {
                if (!code) { printf("REMOTE_LOAD_FAILED\n"); goto fail; }
                dll_base = code; /* Explicitly x86 launcher + x86 child. */
                remote_thread = CreateRemoteThread(child.hProcess, NULL, 0,
                    (LPTHREAD_START_ROUTINE)(dll_base + initialize_offset), NULL, 0, &remote_tid);
                if (!remote_thread) goto fail;
                stage = 3;
            } else if (stage == 3) {
                if (code != READY_MAGIC) { printf("HELPER_INIT_FAILED=%lu\n", code); goto fail; }
                if (!ContinueDebugEvent(event.dwProcessId, event.dwThreadId, status)) goto fail;
                pending = 0;
                if (!DebugActiveProcessStop(child.dwProcessId)) goto fail;
                attached = 0;
                if (remote_path && !VirtualFreeEx(child.hProcess, remote_path, 0, MEM_RELEASE)) goto fail;
                remote_path = NULL;
                if (ResumeThread(child.hThread) != 1) goto fail;
                suspended = 0;
                printf("HELPER_READY=1 DEBUGGER_DETACHED=1 CHILD_RESUMED=1\n");
                FreeLibrary(local_dll); local_dll = NULL;
                CloseHandle(child.hThread); child.hThread = NULL;
                if (WaitForSingleObject(child.hProcess, INFINITE) != WAIT_OBJECT_0 ||
                    !GetExitCodeProcess(child.hProcess, &child_status)) goto fail;
                printf("CHILD_NORMAL_EXIT=%lu\n", child_status);
                CloseHandle(child.hProcess);
                return child_status == 0 ? 0 : 1;
            } else goto fail;
        }
        if (!ContinueDebugEvent(event.dwProcessId, event.dwThreadId, status)) goto fail;
        pending = 0;
    }
    printf("BOOTSTRAP_STARTUP_TIMEOUT\n");
fail:
    printf("BOOTSTRAP_FAILED stage=%d suspended=%d error=%lu\n", stage, suspended, GetLastError());
    /* Only the process just created above. No attach-to-existing/PID argument. */
    if (pending) ContinueDebugEvent(event.dwProcessId, event.dwThreadId, DBG_CONTINUE);
    if (!TerminateProcess(child.hProcess, 90)) printf("CHILD_CLEANUP_ERROR=%lu\n", GetLastError());
    if (attached) DebugActiveProcessStop(child.dwProcessId);
    if (WaitForSingleObject(child.hProcess, 5000) != WAIT_OBJECT_0)
        printf("CHILD_CLEANUP_INCOMPLETE\n");
    if (remote_thread) CloseHandle(remote_thread);
    if (child.hThread) CloseHandle(child.hThread);
    if (child.hProcess) CloseHandle(child.hProcess);
    if (local_dll) FreeLibrary(local_dll);
    return 2;
}
