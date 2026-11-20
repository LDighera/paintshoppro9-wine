#include <windows.h>
__declspec(dllexport) DWORD WINAPI Initialize(void *unused)
{
    (void)unused;
    return 0;
}
BOOL WINAPI DllMain(HINSTANCE m, DWORD reason, LPVOID reserved)
{
    (void)m; (void)reserved;
    return reason != DLL_PROCESS_ATTACH; /* Deliberate loader failure fixture. */
}
