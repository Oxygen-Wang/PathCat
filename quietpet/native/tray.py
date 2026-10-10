"""Windows notification-area icon, using the Tk thread's existing message loop."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import sys
import queue


class GUID(ctypes.Structure):
    _fields_ = [('a', wintypes.DWORD), ('b', wintypes.WORD),
                ('c', wintypes.WORD), ('d', ctypes.c_ubyte * 8)]


class NotifyIconData(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.DWORD), ('hWnd', wintypes.HWND),
                ('uID', wintypes.UINT), ('uFlags', wintypes.UINT),
                ('uCallbackMessage', wintypes.UINT), ('hIcon', wintypes.HICON),
                ('szTip', wintypes.WCHAR * 128), ('dwState', wintypes.DWORD),
                ('dwStateMask', wintypes.DWORD), ('szInfo', wintypes.WCHAR * 256),
                ('uTimeout', wintypes.UINT), ('szInfoTitle', wintypes.WCHAR * 64),
                ('dwInfoFlags', wintypes.DWORD), ('guidItem', GUID),
                ('hBalloonIcon', wintypes.HICON)]


class TrayIcon:
    CALLBACK = 0x8001

    def __init__(self, root, show, quit_app, labels):
        self.root, self.show, self.quit_app, self.labels = root, show, quit_app, labels
        self.hwnd = self.icon = None
        self.added = False
        self.startup_error = None
        self._retry_after = None
        self._closed = False
        self._events = queue.SimpleQueue()
        self._poll_after = None
        if sys.platform != 'win32':
            return
        try:
            self._create()
            self._poll_after = self.root.after(50, self._poll_events)
        except OSError as exc:
            # The pet's own menu remains available without a tray icon.
            self.startup_error = str(exc)
            self.close()

    def _create(self):
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.shell = ctypes.WinDLL('shell32', use_last_error=True)
        self.proc_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND,
                                            wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        signatures = {
            'CreateWindowExW': ([wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, wintypes.HWND, wintypes.HMENU,
                                wintypes.HINSTANCE, ctypes.c_void_p], wintypes.HWND),
            'SetWindowLongPtrW': ([wintypes.HWND, ctypes.c_int, ctypes.c_void_p], ctypes.c_void_p),
            'CallWindowProcW': ([ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
                                wintypes.WPARAM, wintypes.LPARAM], ctypes.c_ssize_t),
            'LoadImageW': ([wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                           ctypes.c_int, ctypes.c_int, wintypes.UINT], wintypes.HANDLE),
            'CreatePopupMenu': ([], wintypes.HMENU),
            'AppendMenuW': ([wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR], wintypes.BOOL),
            'TrackPopupMenu': ([wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int,
                               ctypes.c_int, wintypes.HWND, ctypes.c_void_p], wintypes.UINT),
            'SetForegroundWindow': ([wintypes.HWND], wintypes.BOOL),
            'GetCursorPos': ([ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            'DestroyMenu': ([wintypes.HMENU], wintypes.BOOL),
            'DestroyWindow': ([wintypes.HWND], wintypes.BOOL),
            'DestroyIcon': ([wintypes.HICON], wintypes.BOOL),
            'PostMessageW': ([wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM], wintypes.BOOL),
            'RegisterWindowMessageW': ([wintypes.LPCWSTR], wintypes.UINT),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.user, name)
            function.argtypes, function.restype = args, result
        self.shell.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NotifyIconData)]
        self.shell.Shell_NotifyIconW.restype = wintypes.BOOL
        self.restart_message = self.user.RegisterWindowMessageW('TaskbarCreated')
        self.hwnd = self.user.CreateWindowExW(0, 'STATIC', 'PathCat.Tray', 0,
                                             0, 0, 0, 0, None, None, None, None)
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        self.callback = self.proc_type(self._message)
        self.old_proc = self.user.SetWindowLongPtrW(self.hwnd, -4, ctypes.cast(self.callback, ctypes.c_void_p))
        if not self.old_proc:
            self.close()
            raise ctypes.WinError(ctypes.get_last_error())
        icon_path = Path(__file__).resolve().parents[1] / 'assets' / 'pathcat.ico'
        self.icon = self.user.LoadImageW(None, str(icon_path), 1, 0, 0, 0x10)
        if not self.icon:
            self.close()
            raise ctypes.WinError(ctypes.get_last_error())
        self.data = NotifyIconData()
        self.data.cbSize = ctypes.sizeof(self.data)
        self.data.hWnd, self.data.uID = self.hwnd, 1
        self.data.uFlags, self.data.uCallbackMessage = 0x7, self.CALLBACK
        self.data.hIcon, self.data.szTip = self.icon, 'PathCat · 径猫'
        self._add_to_shell()
        if not self.added:
            self._schedule_retry()

    def _add_to_shell(self):
        self.added = bool(self.shell.Shell_NotifyIconW(0, ctypes.byref(self.data)))
        self.startup_error = None if self.added else 'Could not create PathCat notification-area icon'

    def _schedule_retry(self):
        if not self._closed and self.hwnd and self._retry_after is None:
            self._retry_after = self.root.after(2000, self._retry)

    def _retry(self):
        self._retry_after = None
        if self._closed or not self.hwnd or self.added:
            return
        self._add_to_shell()
        if not self.added:
            self._schedule_retry()

    def _message(self, hwnd, message, wparam, lparam):
        if message == self.CALLBACK:
            if lparam == 0x202:  # WM_LBUTTONUP
                self._events.put('show')
            elif lparam == 0x205:  # WM_RBUTTONUP
                self._events.put('menu')
            return 0
        if message == self.restart_message:
            self._events.put('restart')
            return 0
        return self.user.CallWindowProcW(self.old_proc, hwnd, message, wparam, lparam)

    def _poll_events(self):
        """Never enter Tcl/Tk from a ctypes Windows message callback."""
        self._poll_after = None
        try:
            while not self._closed:
                try:
                    event = self._events.get_nowait()
                except queue.Empty:
                    break
                if event == 'show':
                    self.show()
                elif event == 'menu':
                    self.menu()
                elif event == 'restart':
                    self._add_to_shell()
                    if not self.added:
                        self._schedule_retry()
        finally:
            if not self._closed:
                self._poll_after = self.root.after(50, self._poll_events)

    def menu(self):
        if not self.hwnd:
            return
        menu = self.user.CreatePopupMenu()
        try:
            show_label, quit_label = self.labels()
            self.user.AppendMenuW(menu, 0, 1, show_label)
            self.user.AppendMenuW(menu, 0x800, 0, None)
            self.user.AppendMenuW(menu, 0, 2, quit_label)
            point = wintypes.POINT()
            self.user.GetCursorPos(ctypes.byref(point))
            self.user.SetForegroundWindow(self.hwnd)
            command = self.user.TrackPopupMenu(menu, 0x100 | 0x80 | 0x2,
                                               point.x, point.y, 0, self.hwnd, None)
            self.user.PostMessageW(self.hwnd, 0, 0, 0)
        finally:
            self.user.DestroyMenu(menu)
        if command == 1:
            self.show()
        elif command == 2:
            self.quit_app()

    def close(self):
        self._closed = True
        if self._poll_after is not None:
            self.root.after_cancel(self._poll_after)
            self._poll_after = None
        if self._retry_after is not None:
            self.root.after_cancel(self._retry_after)
            self._retry_after = None
        if self.added:
            self.shell.Shell_NotifyIconW(2, ctypes.byref(self.data))
            self.added = False
        if self.hwnd:
            if getattr(self, 'old_proc', None):
                self.user.SetWindowLongPtrW(self.hwnd, -4, self.old_proc)
            self.user.DestroyWindow(self.hwnd)
            self.hwnd = None
        if self.icon:
            self.user.DestroyIcon(self.icon)
            self.icon = None
