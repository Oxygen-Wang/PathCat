# -*- coding: utf-8 -*-
"""Global summon gesture: key combination (RegisterHotKey) or double-tap Shift."""
import ctypes
import queue
import threading
import time

from ..core.config import IS_WIN

if IS_WIN:
    from ctypes import wintypes
    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32
    LRESULT = ctypes.c_ssize_t
else:  # pragma: no cover
    wintypes = None
    LRESULT = ctypes.c_long

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
HOTKEY_ID = 0x5150

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
VK_SHIFT = 0x10
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
DOUBLE_TAP_SECONDS = 0.45

NAMED_KEYS = {
    'BACKSPACE': 0x08, 'TAB': 0x09, 'ENTER': 0x0D, 'RETURN': 0x0D,
    'ESC': 0x1B, 'ESCAPE': 0x1B, 'SPACE': 0x20,
    'PAGEUP': 0x21, 'PGUP': 0x21, 'PAGEDOWN': 0x22, 'PGDN': 0x22,
    'END': 0x23, 'HOME': 0x24,
    'LEFT': 0x25, 'UP': 0x26, 'RIGHT': 0x27, 'DOWN': 0x28,
    'INSERT': 0x2D, 'INS': 0x2D, 'DELETE': 0x2E, 'DEL': 0x2E,
    'PLUS': 0xBB, 'MINUS': 0xBD, 'COMMA': 0xBC, 'PERIOD': 0xBE,
}

_TAP_WORDS = {
    'SHIFT': 'SHIFT', 'SHIFTSHIFT': 'SHIFT', 'DOUBLESHIFT': 'SHIFT',
    '双击SHIFT': 'SHIFT', '双击SHIFT键': 'SHIFT', '连按SHIFT': 'SHIFT',
    'CTRL': 'CTRL', 'CONTROL': 'CTRL', 'CTRLCTRL': 'CTRL', 'DOUBLECTRL': 'CTRL',
    '双击CTRL': 'CTRL', '连按CTRL': 'CTRL',
    'ALT': 'ALT', 'ALTALT': 'ALT', 'DOUBLEALT': 'ALT',
    '双击ALT': 'ALT', '连按ALT': 'ALT',
    'WIN': 'WIN', 'WINWIN': 'WIN', 'DOUBLEWIN': 'WIN', '双击WIN': 'WIN',
    'WINDOWS': 'WIN', 'META': 'WIN', 'SUPER': 'WIN',
}

_TAP_VKS = {
    'SHIFT': {0x10, 0xA0, 0xA1},
    'CTRL': {0x11, 0xA2, 0xA3},
    'ALT': {0x12, 0xA4, 0xA5},
    'WIN': {0x5B, 0x5C},
}


def tap_gesture(text):
    """Return 'SHIFT' | 'CTRL' | 'ALT' | 'WIN' for a double-tap gesture, else None."""
    key = (text or '').strip().upper().replace(' ', '')
    return _TAP_WORDS.get(key)


def is_shift_gesture(text):
    return tap_gesture(text) == 'SHIFT'


def is_tap_gesture(text):
    return tap_gesture(text) is not None


def parse_hotkey(text):
    """Return (modifiers, virtual_key) for a string like 'Ctrl+Alt+Q', else None."""
    if not text:
        return None
    modifiers = 0
    key = None
    for token in text.replace(' ', '').split('+'):
        name = token.upper()
        if not name:
            continue
        if name in ('CTRL', 'CONTROL'):
            modifiers |= MOD_CONTROL
        elif name == 'ALT':
            modifiers |= MOD_ALT
        elif name == 'SHIFT':
            modifiers |= MOD_SHIFT
        elif name in ('WIN', 'WINDOWS', 'META', 'SUPER'):
            modifiers |= MOD_WIN
        elif name.startswith('F') and name[1:].isdigit() and 1 <= int(name[1:]) <= 24:
            key = 0x70 + int(name[1:]) - 1
        elif name in NAMED_KEYS:
            key = NAMED_KEYS[name]
        elif len(name) == 1 and name.isalnum():
            key = ord(name)
        else:
            return None
    if key is None or modifiers == 0:
        return None
    return modifiers, key


if IS_WIN:
    class _KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [('vkCode', wintypes.DWORD), ('scanCode', wintypes.DWORD),
                    ('flags', wintypes.DWORD), ('time', wintypes.DWORD),
                    ('dwExtraInfo', ctypes.c_void_p)]

    _HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
    _user32.CallNextHookEx.restype = LRESULT
    _user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
    _user32.SetWindowsHookExW.restype = ctypes.c_void_p
    _user32.SetWindowsHookExW.argtypes = [ctypes.c_int, _HOOKPROC, ctypes.c_void_p, wintypes.DWORD]
    _user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
    _user32.RegisterHotKey.restype = wintypes.BOOL
    _user32.GetMessageW.restype = ctypes.c_int
    _user32.GetMessageW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.UINT]
    _user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    _user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    _kernel32.GetModuleHandleW.restype = ctypes.c_void_p
    _kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]


class GlobalHotkey:
    """Register a system-wide summon gesture and report events through a queue.

    Supports either a key combination ('Ctrl+Alt+Q') or the double-tap Shift
    gesture ('Shift'). Events are delivered to the Tk thread via the queue.
    """

    def __init__(self, text, events):
        self.text = text
        self.events = events
        self.thread = None
        self.thread_id = None
        self.tap = tap_gesture(text)
        self.tap_vks = _TAP_VKS.get(self.tap, set())
        self.shift_mode = self.tap == 'SHIFT'
        parsed = parse_hotkey(text)
        self.modifiers, self.vk = parsed if parsed else (0, None)
        self._last_tap = 0.0
        self._hook = None

    @property
    def valid(self):
        return self.tap is not None or self.vk is not None

    def start(self):
        if not IS_WIN or not self.valid:
            return
        self.thread = threading.Thread(target=self._run, name='QuietPetHotkey', daemon=True)
        self.thread.start()

    def _run(self):
        self.thread_id = _kernel32.GetCurrentThreadId()
        if self.tap:
            self._run_tap_hook()
        else:
            self._run_register_hotkey()

    def _run_register_hotkey(self):
        if not _user32.RegisterHotKey(None, HOTKEY_ID, self.modifiers | MOD_NOREPEAT, self.vk):
            self.events.put(('error', self.text))
            return
        self.events.put(('ok', self.text))
        msg = wintypes.MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY:
                self.events.put(('fire', None))
        _user32.UnregisterHotKey(None, HOTKEY_ID)

    def _run_tap_hook(self):
        self._hook = _HOOKPROC(self._hook_handler)
        hmod = _kernel32.GetModuleHandleW(None)
        handle = _user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._hook, hmod, 0)
        if not handle:
            self.events.put(('error', self.text))
            return
        self.events.put(('ok', self.text))
        msg = wintypes.MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            pass
        _user32.UnhookWindowsHookEx(handle)

    def _hook_handler(self, code, wparam, lparam):
        if code >= 0 and wparam in (WM_KEYDOWN, WM_SYSKEYDOWN):
            try:
                kb = ctypes.cast(lparam, ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents
                if kb.vkCode in self.tap_vks:
                    now = time.monotonic()
                    if now - self._last_tap <= DOUBLE_TAP_SECONDS:
                        self._last_tap = 0.0
                        self.events.put(('fire', None))
                    else:
                        self._last_tap = now
            except Exception:
                pass
        return _user32.CallNextHookEx(None, code, wparam, lparam)

    def stop(self):
        if IS_WIN and self.thread_id:
            try:
                _user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass
