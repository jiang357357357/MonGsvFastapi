/* Small CRT-free Windows x64 bootstrap; the Python supervisor owns services. */
typedef unsigned long DWORD;
typedef unsigned short WORD;
typedef unsigned short WCHAR;
typedef int BOOL;
typedef void *HANDLE;
typedef WCHAR *LPWSTR;
typedef const WCHAR *LPCWSTR;
typedef unsigned char *LPBYTE;
typedef struct {
    DWORD cb; LPWSTR reserved; LPWSTR desktop; LPWSTR title;
    DWORD x, y, width, height, chars_x, chars_y, fill, flags;
    WORD show, reserved_size; LPBYTE reserved_data;
    HANDLE input, output, error;
} STARTUPINFOW;
typedef struct { HANDLE process, thread; DWORD process_id, thread_id; } PROCESS_INFORMATION;
#define API __declspec(dllimport)
API DWORD __stdcall GetModuleFileNameW(HANDLE, LPWSTR, DWORD);
API DWORD __stdcall GetFileAttributesW(LPCWSTR);
API LPWSTR __stdcall GetCommandLineW(void);
API BOOL __stdcall CreateProcessW(LPCWSTR, LPWSTR, void *, void *, BOOL, DWORD, void *, LPCWSTR, STARTUPINFOW *, PROCESS_INFORMATION *);
API DWORD __stdcall WaitForSingleObject(HANDLE, DWORD);
API BOOL __stdcall GetExitCodeProcess(HANDLE, DWORD *);
API BOOL __stdcall CloseHandle(HANDLE);
API void __stdcall ExitProcess(DWORD);
API int __stdcall MessageBoxW(HANDLE, LPCWSTR, LPCWSTR, unsigned int);
static WCHAR root[32768], python[32768], command[32768];
static STARTUPINFOW startup;
static PROCESS_INFORMATION process;
static unsigned int used;
static BOOL append(LPCWSTR text) {
    while (*text) { if (used >= 32766) return 0; command[used++] = *text++; }
    command[used] = 0; return 1;
}
void mainCRTStartup(void) {
    DWORD length = GetModuleFileNameW(0, root, 32768), code = 1;
    unsigned int i = 0;
    LPWSTR args;
    if (!length || length >= 32768) ExitProcess(1);
    while (length && root[length - 1] != '\\') --length;
    if (!length || length + 20 >= 32768) ExitProcess(1);
    root[length - 1] = 0;
    while (root[i]) { python[i] = root[i]; ++i; }
    { LPCWSTR suffix = L"\\runtime\\python.exe"; while (*suffix) python[i++] = *suffix++; python[i] = 0; }
    if (GetFileAttributesW(python) == 0xFFFFFFFFul) {
        MessageBoxW(0, L"Windows Python runtime is missing. Please copy the complete MonGSV folder.", L"MonGSV", 0x10);
        ExitProcess(1);
    }
    if (!append(L"\"") || !append(python) || !append(L"\" -s \"") || !append(root) || !append(L"\\launcher.py\" ")) ExitProcess(1);
    args = GetCommandLineW();
    if (*args == '"') { ++args; while (*args && *args != '"') ++args; if (*args) ++args; }
    else { while (*args && *args != ' ' && *args != '\t') ++args; }
    if (!append(args)) ExitProcess(1);
    startup.cb = sizeof(startup);
    if (!CreateProcessW(python, command, 0, 0, 1, 0, 0, root, &startup, &process)) {
        MessageBoxW(0, L"Could not start Python. Run Check.cmd for diagnostics and install the Microsoft Visual C++ x64 runtime if needed.", L"MonGSV", 0x10);
        ExitProcess(1);
    }
    CloseHandle(process.thread);
    WaitForSingleObject(process.process, 0xFFFFFFFFul);
    GetExitCodeProcess(process.process, &code);
    CloseHandle(process.process);
    if (code) MessageBoxW(0, L"MonGSV stopped with an error. Run Check.cmd and inspect data\\launcher\\console.log for details.", L"MonGSV", 0x10);
    ExitProcess(code);
}
