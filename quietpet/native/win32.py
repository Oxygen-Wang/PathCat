# -*- coding: utf-8 -*-
"""Windows-only helpers: keep-on-top, Explorer drop target, OLE drag source.

Dragging supports two payloads:
  * real files/folders  -> CF_HDROP (via the shell data object)
  * text (e.g. "@skill") -> CF_UNICODETEXT (custom IDataObject)
so non-file entries like skills and MCP can be dragged into other apps.
"""
import ctypes
import struct
from pathlib import Path

from ..core.config import IS_WIN

def foreground_process_id():
    """Identify the active application, including our own dialogs and menus."""
    if not IS_WIN:
        return None
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value or None


def make_drag_overlay_clickthrough(hwnd):
    """Keep the decorative drag window out of mouse hit tests and focus."""
    if not IS_WIN:
        return
    user32 = ctypes.windll.user32
    from ctypes import wintypes
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    top = user32.GetAncestor(hwnd, 2) or hwnd
    get_style = user32.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.GetWindowLongW
    set_style = user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.SetWindowLongW
    get_style.argtypes = [wintypes.HWND, ctypes.c_int]
    get_style.restype = ctypes.c_ssize_t
    set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    set_style.restype = ctypes.c_ssize_t
    # WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
    set_style(top, -20, get_style(top, -20) | 0x80000 | 0x20 | 0x08000000 | 0x80)

if IS_WIN:
    from ctypes import wintypes

    _user32 = ctypes.windll.user32
    _shell32 = ctypes.windll.shell32
    _ole32 = ctypes.windll.ole32
    _kernel32 = ctypes.windll.kernel32

    def control_button_down():
        return bool(_user32.GetAsyncKeyState(0x11) & 0x8000)

    LRESULT = ctypes.c_ssize_t
    HRESULT = ctypes.c_long
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    _user32.SetWindowLongPtrW.restype = ctypes.c_void_p
    _user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, WNDPROC]
    _user32.CallWindowProcW.restype = LRESULT
    _user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
                                        wintypes.WPARAM, wintypes.LPARAM]
    _user32.SetWindowPos.restype = wintypes.BOOL
    _user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                     ctypes.c_int, ctypes.c_int, wintypes.UINT]
    _shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
    _shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, ctypes.c_wchar_p, wintypes.UINT]
    _shell32.DragQueryFileW.restype = wintypes.UINT
    _shell32.DragFinish.argtypes = [wintypes.HANDLE]

    HWND_TOPMOST = -1
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOACTIVATE = 0x0010

    def force_top(hwnd):
        try:
            _user32.SetWindowPos(int(hwnd), HWND_TOPMOST, 0, 0, 0, 0,
                                 SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
        except Exception:
            pass

    class DropTarget:
        """Use OLE without replacing Tk's window procedure."""

        def __init__(self, hwnd, on_drop):
            self.hwnd = int(hwnd)
            if not register_drop_target(self.hwnd, lambda paths, copy, point: on_drop(paths)):
                raise OSError('Could not register file drop target')

    # --- cursor helpers ----------------------------------------------------
    class _POINT(ctypes.Structure):
        _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

    _user32.GetCursorPos.argtypes = [ctypes.POINTER(_POINT)]
    _user32.GetCursorPos.restype = wintypes.BOOL
    _user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    _user32.GetAsyncKeyState.restype = ctypes.c_short

    def get_cursor_pos():
        pt = _POINT()
        _user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def left_button_down():
        return bool(_user32.GetAsyncKeyState(0x01) & 0x8000)

    # --- OLE constants -----------------------------------------------------
    DROPEFFECT_COPY = 1
    S_OK = 0
    S_FALSE = 1
    E_NOINTERFACE = -2147467262
    E_NOTIMPL = -2147467263
    DV_E_FORMATETC = -2147221404
    DRAGDROP_S_DROP = 0x00040100
    DRAGDROP_S_CANCEL = 0x00040101
    DRAGDROP_S_USEDEFAULTCURSORS = 0x00040102
    MK_LBUTTON = 0x0001

    CF_UNICODETEXT = 13
    CF_HDROP = 15
    DVASPECT_CONTENT = 1
    TYMED_HGLOBAL = 1
    GMEM_MOVEABLE = 0x0002

    class GUID(ctypes.Structure):
        _fields_ = [('Data1', ctypes.c_ulong), ('Data2', ctypes.c_ushort),
                    ('Data3', ctypes.c_ushort), ('Data4', ctypes.c_ubyte * 8)]

    class FORMATETC(ctypes.Structure):
        _fields_ = [('cfFormat', ctypes.c_ushort), ('ptd', ctypes.c_void_p),
                    ('dwAspect', ctypes.c_ulong), ('lindex', ctypes.c_long),
                    ('tymed', ctypes.c_ulong)]

    class STGMEDIUM(ctypes.Structure):
        _fields_ = [('tymed', ctypes.c_ulong), ('unionmember', ctypes.c_void_p),
                    ('pUnkForRelease', ctypes.c_void_p)]

    _kernel32.GlobalAlloc.restype = ctypes.c_void_p
    _kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    _kernel32.GlobalLock.restype = ctypes.c_void_p
    _kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    _kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]

    # --- drop source -------------------------------------------------------
    _QI_FN = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
    _REF_FN = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
    _QCD_FN = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, wintypes.BOOL, wintypes.DWORD)
    _GF_FN = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, wintypes.DWORD)

    class IDropSourceVtbl(ctypes.Structure):
        _fields_ = [('QueryInterface', _QI_FN), ('AddRef', _REF_FN), ('Release', _REF_FN),
                    ('QueryContinueDrag', _QCD_FN), ('GiveFeedback', _GF_FN)]

    class DropSource(ctypes.Structure):
        _fields_ = [('lpVtbl', ctypes.POINTER(IDropSourceVtbl)), ('ref', ctypes.c_ulong)]

    _drop_source_ref = None

    def _make_drop_source(on_drag=None):
        global _drop_source_ref

        def qi(this, riid, ppv):
            return E_NOINTERFACE

        def addref(this):
            return 2

        def release(this):
            return 1

        def query_continue_drag(this, escaped, keystate):
            if escaped:
                return DRAGDROP_S_CANCEL
            if not (keystate & MK_LBUTTON):
                return DRAGDROP_S_DROP
            if on_drag:
                try:
                    on_drag(get_cursor_pos())
                except Exception:
                    pass
            return S_OK

        def give_feedback(this, effect):
            return DRAGDROP_S_USEDEFAULTCURSORS

        vtbl = IDropSourceVtbl(_QI_FN(qi), _REF_FN(addref), _REF_FN(release),
                               _QCD_FN(query_continue_drag), _GF_FN(give_feedback))
        src = DropSource(ctypes.pointer(vtbl), 1)
        _drop_source_ref = (vtbl, src)
        return src

    # --- file data object (CF_HDROP) via the shell -------------------------
    _shell32.ILClone.argtypes = [ctypes.c_void_p]
    _shell32.ILClone.restype = ctypes.c_void_p
    _shell32.ILFindLastID.argtypes = [ctypes.c_void_p]
    _shell32.ILFindLastID.restype = ctypes.c_void_p
    _shell32.ILRemoveLastID.argtypes = [ctypes.c_void_p]
    _shell32.ILRemoveLastID.restype = wintypes.BOOL
    _shell32.ILFree.argtypes = [ctypes.c_void_p]
    _shell32.ILFree.restype = None
    _shell32.SHParseDisplayName.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p,
                                            ctypes.POINTER(ctypes.c_void_p), ctypes.c_ulong,
                                            ctypes.POINTER(ctypes.c_ulong)]
    _shell32.SHParseDisplayName.restype = HRESULT
    _shell32.SHCreateDataObject.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                            ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p,
                                            ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
    _shell32.SHCreateDataObject.restype = HRESULT
    _ole32.CLSIDFromString.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(GUID)]
    _ole32.CLSIDFromString.restype = HRESULT
    _ole32.ReleaseStgMedium.argtypes = [ctypes.POINTER(STGMEDIUM)]
    _ole32.ReleaseStgMedium.restype = None
    _ole32.RegisterDragDrop.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    _ole32.RegisterDragDrop.restype = HRESULT
    _ole32.RevokeDragDrop.argtypes = [ctypes.c_void_p]
    _ole32.RevokeDragDrop.restype = HRESULT

    def _make_file_object(paths):
        if isinstance(paths, (str, Path)):
            paths = [paths]
        paths = [Path(p) for p in paths if Path(p).exists()]
        if not paths:
            return None
        parent_key = str(paths[0].parent).lower()
        paths = [p for p in paths if str(p.parent).lower() == parent_key]
        pidls = []
        for p in paths:
            pidl = ctypes.c_void_p()
            if _shell32.SHParseDisplayName(str(p), None, ctypes.byref(pidl), 0, None) == 0 and pidl:
                pidls.append(pidl)
        if not pidls:
            return None
        parent = _shell32.ILClone(pidls[0])
        _shell32.ILRemoveLastID(parent)
        children = (ctypes.c_void_p * len(pidls))(*[_shell32.ILFindLastID(p) for p in pidls])
        iid = GUID()
        _ole32.CLSIDFromString('{0000010E-0000-0000-C000-000000000046}', ctypes.byref(iid))
        pdo = ctypes.c_void_p()
        hr = _shell32.SHCreateDataObject(parent, len(pidls), children, None,
                                         ctypes.byref(iid), ctypes.byref(pdo))
        _shell32.ILFree(parent)
        for pidl in pidls:
            _shell32.ILFree(pidl)
        return pdo if hr == 0 else None

    # --- text data object (CF_UNICODETEXT) ---------------------------------
    _GD_FN = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(FORMATETC), ctypes.POINTER(STGMEDIUM))
    _QG_FN = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(FORMATETC))
    _GCE_FN = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(FORMATETC), ctypes.POINTER(FORMATETC))
    _SD_FN = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(FORMATETC),
                                ctypes.POINTER(STGMEDIUM), wintypes.BOOL)
    _EFE_FN = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p))
    _DA_FN = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(FORMATETC),
                                wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD))
    _DU_FN = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, wintypes.DWORD)
    _ED_FN = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))

    class IDataObjectVtbl(ctypes.Structure):
        _fields_ = [('QueryInterface', _QI_FN), ('AddRef', _REF_FN), ('Release', _REF_FN),
                    ('GetData', _GD_FN), ('GetDataHere', _GD_FN),
                    ('QueryGetData', _QG_FN), ('GetCanonicalFormatEtc', _GCE_FN),
                    ('SetData', _SD_FN), ('EnumFormatEtc', _EFE_FN),
                    ('DAdvise', _DA_FN), ('DUnadvise', _DU_FN), ('EnumDAdvise', _ED_FN)]

    class DataObject(ctypes.Structure):
        _fields_ = [('lpVtbl', ctypes.POINTER(IDataObjectVtbl)), ('ref', ctypes.c_ulong)]

    _EN_NEXT = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.c_ulong,
                                  ctypes.POINTER(FORMATETC), ctypes.POINTER(ctypes.c_ulong))
    _EN_SKIP = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.c_ulong)
    _EN_0 = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p)
    _EN_CLONE = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))

    class IEnumFORMATETCVtbl(ctypes.Structure):
        _fields_ = [('QueryInterface', _QI_FN), ('AddRef', _REF_FN), ('Release', _REF_FN),
                    ('Next', _EN_NEXT), ('Skip', _EN_SKIP), ('Reset', _EN_0), ('Clone', _EN_CLONE)]

    class FormatEnum(ctypes.Structure):
        _fields_ = [('lpVtbl', ctypes.POINTER(IEnumFORMATETCVtbl)), ('ref', ctypes.c_ulong),
                    ('index', ctypes.c_ulong)]

    _text_value = ''
    _file_paths = []
    _fmt_list = []
    _data_obj_ref = None
    _enum_ref = None
    _hdrop_handles = []

    def _make_hdrop(paths):
        """Build an HGLOBAL CF_HDROP (DROPFILES + double-null-terminated wide paths)."""
        blob = ''.join(str(p) + '\x00' for p in paths) + '\x00'
        data = blob.encode('utf-16-le')
        header_size = 20  # DROPFILES: DWORD + POINT(2 longs) + BOOL + BOOL
        handle = _kernel32.GlobalAlloc(GMEM_MOVEABLE, header_size + len(data))
        ptr = _kernel32.GlobalLock(handle)
        header = struct.pack('<IiiII', header_size, 0, 0, 0, 1)  # pFiles, pt, fNC, fWide
        ctypes.memmove(ptr, header + data, header_size + len(data))
        _kernel32.GlobalUnlock(handle)
        return handle

    def _make_text_handle(text):
        raw = text.encode('utf-16-le') + b'\x00\x00'
        handle = _kernel32.GlobalAlloc(GMEM_MOVEABLE, len(raw))
        ptr = _kernel32.GlobalLock(handle)
        ctypes.memmove(ptr, raw, len(raw))
        _kernel32.GlobalUnlock(handle)
        return handle

    def _obj_qi(this, riid, ppv):
        return E_NOINTERFACE

    def _obj_addref(this):
        return 2

    def _obj_release(this):
        return 1

    def _obj_getdata(this, pfe, pmed):
        fe = pfe.contents
        handle = None
        if fe.cfFormat == CF_UNICODETEXT and _text_value:
            handle = _make_text_handle(_text_value)
        elif fe.cfFormat == CF_HDROP and _file_paths:
            handle = _make_hdrop(_file_paths)
        if handle is None:
            return DV_E_FORMATETC
        med = pmed.contents
        med.tymed = TYMED_HGLOBAL
        med.unionmember = handle
        med.pUnkForRelease = None
        return S_OK

    def _obj_querygetdata(this, pfe):
        cf = pfe.contents.cfFormat
        if cf == CF_UNICODETEXT and _text_value:
            return S_OK
        if cf == CF_HDROP and _file_paths:
            return S_OK
        return DV_E_FORMATETC

    def _obj_notimpl_gd(this, pfe, pmed):
        return E_NOTIMPL

    def _obj_notimpl_gce(this, a, b):
        return E_NOTIMPL

    def _obj_notimpl_set(this, a, b, c):
        return E_NOTIMPL

    def _obj_notimpl_da(this, a, b, c, d):
        return E_NOTIMPL

    def _obj_notimpl_du(this, a):
        return E_NOTIMPL

    def _obj_notimpl_ed(this, a):
        return E_NOTIMPL

    def _enum_next(this, celt, rgelt, pcfetched):
        e = _enum_ref[1] if _enum_ref else None
        if e is None or not rgelt or celt == 0 or e.index >= len(_fmt_list):
            if pcfetched:
                pcfetched[0] = 0
            return S_FALSE
        rgelt[0] = _fmt_list[e.index]
        e.index += 1
        if pcfetched:
            pcfetched[0] = 1
        return S_OK

    def _enum_skip(this, celt):
        if _enum_ref:
            _enum_ref[1].index += celt
        return S_OK

    def _enum_reset(this):
        if _enum_ref:
            _enum_ref[1].index = 0
        return S_OK

    def _enum_clone(this, ppenum):
        return E_NOTIMPL

    def _obj_enumformatetc(this, direction, ppenum):
        global _enum_ref
        if not ppenum:
            return E_NOTIMPL
        vtbl = IEnumFORMATETCVtbl(_QI_FN(_obj_qi), _REF_FN(_obj_addref), _REF_FN(_obj_release),
                                  _EN_NEXT(_enum_next), _EN_SKIP(_enum_skip),
                                  _EN_0(_enum_reset), _EN_CLONE(_enum_clone))
        enum = FormatEnum(ctypes.pointer(vtbl), 1, 0)
        _enum_ref = (vtbl, enum)
        ppenum[0] = ctypes.cast(ctypes.pointer(enum), ctypes.c_void_p)
        return S_OK

    def _make_object(text=None, files=None):
        """A custom IDataObject offering CF_UNICODETEXT and/or CF_HDROP."""
        global _text_value, _file_paths, _fmt_list, _data_obj_ref, _enum_ref
        _text_value = text or ''
        _file_paths = [str(p) for p in (files or [])]
        _fmt_list = []
        if _text_value:
            _fmt_list.append(FORMATETC(CF_UNICODETEXT, None, DVASPECT_CONTENT, -1, TYMED_HGLOBAL))
        if _file_paths:
            _fmt_list.append(FORMATETC(CF_HDROP, None, DVASPECT_CONTENT, -1, TYMED_HGLOBAL))
        _enum_ref = None
        vtbl = IDataObjectVtbl(_QI_FN(_obj_qi), _REF_FN(_obj_addref), _REF_FN(_obj_release),
                               _GD_FN(_obj_getdata), _GD_FN(_obj_notimpl_gd),
                               _QG_FN(_obj_querygetdata), _GCE_FN(_obj_notimpl_gce),
                               _SD_FN(_obj_notimpl_set), _EFE_FN(_obj_enumformatetc),
                               _DA_FN(_obj_notimpl_da), _DU_FN(_obj_notimpl_du),
                               _ED_FN(_obj_notimpl_ed))
        obj = DataObject(ctypes.pointer(vtbl), 1)
        _data_obj_ref = (vtbl, obj)
        return obj

    def _make_text_object(text):
        return _make_object(text=text)

    # --- drag entry point --------------------------------------------------
    _ole_ready = False
    last_drag_error = None
    last_drag_effect = None

    def _ensure_ole():
        global _ole_ready
        if not _ole_ready:
            try:
                _ole32.OleInitialize(None)
            except Exception:
                pass
            _ole_ready = True

    def _release_com(p):
        try:
            vt = ctypes.cast(p, ctypes.POINTER(ctypes.c_void_p))[0]
            funcs = ctypes.cast(vt, ctypes.POINTER(ctypes.c_void_p))
            release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(funcs[2])
            release(p)
        except Exception:
            pass

    _ole32.DoDragDrop.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                                  ctypes.POINTER(wintypes.DWORD)]
    _ole32.DoDragDrop.restype = HRESULT

    def start_ole_drag(paths=None, text=None, text_file=None, on_drag=None):
        """Start a native drag.

        paths     -> real files/folders via the shell (CF_HDROP)
        text      -> CF_UNICODETEXT (e.g. "@skill-id")
        text_file -> also expose this path as CF_HDROP alongside text
        """
        global last_drag_error, last_drag_effect
        paths = [Path(p) for p in (paths or []) if Path(p).exists()]
        import os as _os
        _log = _os.environ.get('QP_DRAG_LOG')
        if _log:
            try:
                with open(_log, 'a', encoding='utf-8') as f:
                    f.write('start paths=%r text=%r\n' % (paths, text))
            except Exception:
                pass
        try:
            _ensure_ole()
            releaser = None
            if paths:
                ptr = _make_file_object(paths)
                if not ptr:
                    last_drag_error = 'SHCreateDataObject returned NULL'
                    return
                releaser = lambda: _release_com(ptr)
            elif text or text_file:
                files = [text_file] if text_file and Path(text_file).exists() else None
                obj = _make_object(text=text, files=files)
                ptr = ctypes.cast(ctypes.byref(obj), ctypes.c_void_p)
            else:
                return
            src = _make_drop_source(on_drag=on_drag)
            effect = wintypes.DWORD(DROPEFFECT_COPY)
            hr = _ole32.DoDragDrop(ptr, ctypes.cast(ctypes.byref(src), ctypes.c_void_p),
                                   DROPEFFECT_COPY, ctypes.byref(effect))
            last_drag_effect = (hr, effect.value)
            if _log:
                try:
                    with open(_log, 'a', encoding='utf-8') as f:
                        f.write('end effect=%r err=%r\n' % (last_drag_effect, last_drag_error))
                except Exception:
                    pass
            if releaser:
                releaser()
        except Exception as exc:  # keep the UI alive but make failures visible
            last_drag_error = repr(exc)
            try:
                import sys as _sys
                print('QuietPet drag error:', exc, file=_sys.stderr)
            except Exception:
                pass

    def install_drop_targets(widget, callback, sink):
        targets = []

        def walk(w):
            targets.append(w)
            for child in w.winfo_children():
                walk(child)

        try:
            walk(widget)
        except Exception:
            targets = [widget]
        for w in targets:
            try:
                sink.append(DropTarget(w.winfo_id(), callback))
            except Exception:
                pass

    # --- OLE drop target (single drag handles internal + external drops) ----
    DROPEFFECT_MOVE = 2
    MK_CONTROL = 0x0008

    class POINTL(ctypes.Structure):
        _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

    _DT_EFFECT_FN = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                                       POINTL, ctypes.POINTER(wintypes.DWORD))
    _DT_OVER_FN = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, wintypes.DWORD,
                                     POINTL, ctypes.POINTER(wintypes.DWORD))
    _DT_LEAVE_FN = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p)

    class IDropTargetVtbl(ctypes.Structure):
        _fields_ = [('QueryInterface', _QI_FN), ('AddRef', _REF_FN), ('Release', _REF_FN),
                    ('DragEnter', _DT_EFFECT_FN), ('DragOver', _DT_OVER_FN),
                    ('DragLeave', _DT_LEAVE_FN), ('Drop', _DT_EFFECT_FN)]

    class DropTargetObj(ctypes.Structure):
        _fields_ = [('lpVtbl', ctypes.POINTER(IDropTargetVtbl)), ('ref', ctypes.c_ulong)]

    _target_refs = {}
    _target_cb = None
    _target_drag_cb = None
    _target_drag_files = False
    _target_point = (0, 0)

    def _read_hdrop(pdata):
        fe = FORMATETC(CF_HDROP, None, DVASPECT_CONTENT, -1, TYMED_HGLOBAL)
        med = STGMEDIUM()
        vt = ctypes.cast(pdata, ctypes.POINTER(ctypes.c_void_p))[0]
        funcs = ctypes.cast(vt, ctypes.POINTER(ctypes.c_void_p))
        get_data = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(FORMATETC),
                                      ctypes.POINTER(STGMEDIUM))(funcs[3])
        if get_data(pdata, ctypes.byref(fe), ctypes.byref(med)) != 0:
            return []
        paths = []
        try:
            count = _shell32.DragQueryFileW(med.unionmember, 0xFFFFFFFF, None, 0)
            for i in range(count):
                length = _shell32.DragQueryFileW(med.unionmember, i, None, 0)
                buf = ctypes.create_unicode_buffer(length + 1)
                _shell32.DragQueryFileW(med.unionmember, i, buf, length + 1)
                if buf.value:
                    paths.append(buf.value)
        finally:
            _ole32.ReleaseStgMedium(ctypes.byref(med))
        return paths

    def _t_qi(this, riid, ppv):
        return E_NOINTERFACE

    def _t_addref(this):
        return 2

    def _t_release(this):
        return 1

    def _t_enter(this, pdata, keystate, pt, peffect):
        global _target_point, _target_drag_files
        _target_point = (pt.x, pt.y)
        _target_drag_files = bool(_read_hdrop(pdata))
        _notify_target_drag(_target_point if _target_drag_files else None)
        peffect[0] = DROPEFFECT_COPY
        return S_OK

    def _t_over(this, keystate, pt, peffect):
        global _target_point
        _target_point = (pt.x, pt.y)
        if _target_drag_files:
            _notify_target_drag(_target_point)
        peffect[0] = DROPEFFECT_COPY
        return S_OK

    def _t_leave(this):
        _notify_target_drag(None)
        return S_OK

    def _notify_target_drag(point):
        if _target_drag_cb:
            try:
                _target_drag_cb(point)
            except Exception:
                pass

    def _t_drop(this, pdata, keystate, pt, peffect):
        _notify_target_drag(None)
        paths = _read_hdrop(pdata)
        copy = bool(keystate & MK_CONTROL)
        if _target_cb and paths:
            try:
                _target_cb(paths, copy, (pt.x, pt.y))
            except Exception:
                pass
        peffect[0] = DROPEFFECT_COPY if copy else DROPEFFECT_MOVE
        return S_OK

    def revoke_drop_target(hwnd):
        try:
            _ole32.RevokeDragDrop(int(hwnd))
            _target_refs.pop(int(hwnd), None)
        except Exception:
            pass

    def register_drop_target(hwnd, callback, on_drag=None):
        """Keep each window's callbacks and COM object alive independently."""
        try:
            _ensure_ole()
            has_files = False

            def notify(point):
                if on_drag:
                    on_drag(point)

            def enter(this, pdata, keystate, pt, effect):
                nonlocal has_files
                has_files = bool(_read_hdrop(pdata))
                try:
                    notify((pt.x, pt.y) if has_files else None)
                except Exception:
                    pass
                effect[0] = DROPEFFECT_COPY if has_files else 0
                return S_OK

            def over(this, keystate, pt, effect):
                if has_files:
                    try:
                        notify((pt.x, pt.y))
                    except Exception:
                        pass
                effect[0] = DROPEFFECT_COPY if has_files else 0
                return S_OK

            def leave(this):
                try:
                    notify(None)
                except Exception:
                    pass
                return S_OK

            def drop(this, pdata, keystate, pt, effect):
                leave(this)
                paths = _read_hdrop(pdata)
                copy = bool(keystate & MK_CONTROL)
                if paths:
                    try:
                        callback(paths, copy, (pt.x, pt.y))
                    except Exception:
                        effect[0] = 0
                        return S_OK
                effect[0] = DROPEFFECT_COPY if paths else 0
                return S_OK

            vtbl = IDropTargetVtbl(_QI_FN(_t_qi), _REF_FN(_t_addref), _REF_FN(_t_release),
                                   _DT_EFFECT_FN(enter), _DT_OVER_FN(over),
                                   _DT_LEAVE_FN(leave), _DT_EFFECT_FN(drop))
            obj = DropTargetObj(ctypes.pointer(vtbl), 1)
            hr = _ole32.RegisterDragDrop(int(hwnd), ctypes.cast(ctypes.byref(obj), ctypes.c_void_p))
            if hr == 0:
                _target_refs[int(hwnd)] = (vtbl, obj)
                return True
            return False
        except Exception:
            return False

else:  # pragma: no cover - non-Windows fallback
    def control_button_down():
        return False
    def revoke_drop_target(hwnd):
        pass

    def force_top(hwnd):
        pass

    def _ensure_ole():
        pass

    def start_ole_drag(paths=None, text=None, text_file=None, on_drag=None):
        pass

    def get_cursor_pos():
        return (0, 0)

    def left_button_down():
        return False

    def install_drop_targets(widget, callback, sink):
        pass

    def register_drop_target(hwnd, callback, on_drag=None):
        return False
