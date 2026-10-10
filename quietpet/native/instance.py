"""Hold a Windows session mutex for the entire desktop application's lifetime."""
import ctypes
import sys
from ctypes import wintypes


class SingleInstance:
    def __init__(self, name=r'Local\PathCat.Desktop'):
        self.name = name
        self.handle = None

    def acquire(self):
        if sys.platform != 'win32':
            return True
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel.CreateMutexW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        ctypes.set_last_error(0)
        handle = kernel.CreateMutexW(None, False, self.name)
        error = ctypes.get_last_error()
        if not handle:
            raise ctypes.WinError(error)
        if error == 183:  # ERROR_ALREADY_EXISTS, including a concurrent launch
            kernel.CloseHandle(handle)
            return False
        self.handle = handle
        return True

    def close(self):
        if self.handle is not None:
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle(self.handle)
            self.handle = None


def notify_running():
    ctypes.windll.user32.MessageBoxW(
        None, 'PathCat 已在运行，请使用桌面上的小猫。\n'
        'PathCat is already running. Please use the existing cat.',
        'PathCat', 0x40)
