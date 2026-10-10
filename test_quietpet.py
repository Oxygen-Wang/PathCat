# -*- coding: utf-8 -*-
"""Tests for QuietPet core logic. Run:  python -m unittest test_quietpet -v"""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from quietpet.gestures import hotkey
from quietpet.opencode import status
from quietpet.core import util


class TestHotkey(unittest.TestCase):
    def test_parse_basic(self):
        self.assertEqual(hotkey.parse_hotkey('Ctrl+Alt+Q'),
                         (hotkey.MOD_CONTROL | hotkey.MOD_ALT, ord('Q')))

    def test_parse_case_and_spaces(self):
        self.assertEqual(hotkey.parse_hotkey('ctrl + alt + q'), (3, 81))

    def test_parse_named_keys(self):
        self.assertEqual(hotkey.parse_hotkey('Win+Shift+Space'),
                         (hotkey.MOD_WIN | hotkey.MOD_SHIFT, 0x20))
        self.assertEqual(hotkey.parse_hotkey('Alt+Enter'), (hotkey.MOD_ALT, 0x0D))

    def test_parse_function_key(self):
        self.assertEqual(hotkey.parse_hotkey('Ctrl+F5'), (hotkey.MOD_CONTROL, 0x74))
        self.assertEqual(hotkey.parse_hotkey('Ctrl+F24'), (hotkey.MOD_CONTROL, 0x70 + 23))

    def test_parse_invalid(self):
        for bad in ('Bad', 'Space+A', '', None, 'Ctrl+', 'Ctrl+Nope'):
            self.assertIsNone(hotkey.parse_hotkey(bad))

    def test_shift_gesture(self):
        for good in ('Shift', ' shift ', '双击Shift', 'Double Shift', 'SHIFTSHIFT'):
            self.assertTrue(hotkey.is_shift_gesture(good), good)
        self.assertFalse(hotkey.is_shift_gesture('Ctrl+Shift+Q'))

    def test_tap_gestures(self):
        self.assertEqual(hotkey.tap_gesture('Alt'), 'ALT')
        self.assertEqual(hotkey.tap_gesture('双击Alt'), 'ALT')
        self.assertEqual(hotkey.tap_gesture('Ctrl'), 'CTRL')
        self.assertEqual(hotkey.tap_gesture('Win'), 'WIN')
        self.assertTrue(hotkey.is_tap_gesture('Alt'))
        self.assertIsNone(hotkey.tap_gesture('Ctrl+Alt+Q'))

    def test_default_hotkey_is_tap(self):
        from quietpet.core import config
        self.assertTrue(hotkey.is_tap_gesture(config.DEFAULT_HOTKEY))

    def test_global_hotkey_shift_mode(self):
        gh = hotkey.GlobalHotkey('Shift', None)
        self.assertTrue(gh.valid)
        self.assertTrue(gh.shift_mode)

    def test_global_hotkey_combo_mode(self):
        gh = hotkey.GlobalHotkey('Ctrl+Alt+Q', None)
        self.assertTrue(gh.valid)
        self.assertFalse(gh.shift_mode)


class TestSafeName(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(util.safe_name(' hello '), 'hello')
        self.assertEqual(util.safe_name('报告 2026'), '报告 2026')

    def test_invalid(self):
        for bad in ('', '  ', 'a/b', 'a\\b', 'a:b', 'a*b', 'a?b', 'a"b',
                    'a<b', 'a>b', 'a|b', 'x.', '.', '..'):
            with self.assertRaises(ValueError, msg=repr(bad)):
                util.safe_name(bad)

    def test_trailing_space_is_trimmed(self):
        self.assertEqual(util.safe_name('x '), 'x')


class TestUniqueDest(unittest.TestCase):
    def test_no_collision(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(util.unique_dest(Path(d), 'new.txt').name, 'new.txt')

    def test_collision_numbers(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / 'a.txt').write_text('x')
            self.assertEqual(util.unique_dest(d, 'a.txt').name, 'a (2).txt')
            (d / 'a (2).txt').write_text('x')
            self.assertEqual(util.unique_dest(d, 'a.txt').name, 'a (3).txt')


class TestStripJsonc(unittest.TestCase):
    def test_comments_and_trailing_commas(self):
        text = '{\n // line\n "a": 1, /* block */\n "b": [1, 2,],\n}'
        self.assertEqual(json.loads(util.strip_jsonc(text)), {'a': 1, 'b': [1, 2]})

    def test_url_not_broken(self):
        text = '{"url": "https://example.com/x"}'
        self.assertEqual(json.loads(util.strip_jsonc(text))['url'], 'https://example.com/x')


class TestSkillsAndMcp(unittest.TestCase):
    def test_iter_skills_flat_and_dir(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'skills'
            root.mkdir(parents=True)
            (root / 'review.md').write_text('---\nname: Review\ndescription: do review\n---\nbody')
            (root / 'git-release').mkdir()
            (root / 'git-release' / 'SKILL.md').write_text('---\nname: Git Release\ndescription: rel\n---\n')
            (root / 'note.txt').write_text('x')
            found = {sid: md for sid, md in status._iter_skills_in(root)}
            self.assertIn('review', found)
            self.assertIn('git-release', found)
            self.assertNotIn('note', found)

    def test_frontmatter(self):
        with tempfile.TemporaryDirectory() as d:
            md = Path(d) / 'SKILL.md'
            md.write_text('---\nname: My Skill\ndescription: does things\n---\nbody')
            self.assertEqual(status._frontmatter(md), ('My Skill', 'does things'))

    def test_read_skill_text_strips_frontmatter(self):
        with tempfile.TemporaryDirectory() as d:
            md = Path(d) / 'SKILL.md'
            md.write_text('---\nname: X\ndescription: y\n---\n\n# Body\n\nHello\n')
            text = status.read_skill_text(md)
            self.assertIn('# Body', text)
            self.assertNotIn('name:', text)

    def test_read_skill_text_truncates(self):
        with tempfile.TemporaryDirectory() as d:
            md = Path(d) / 'SKILL.md'
            md.write_text('x' * 5000)
            self.assertLessEqual(len(status.read_skill_text(md, limit=100)), 101)

    def test_list_skills_shape(self):
        skills = status.list_open_skills(project_dir=None, config_paths=[])
        self.assertIsInstance(skills, list)
        for s in skills:
            self.assertTrue({'id', 'name', 'description', 'path'} <= set(s))

    def test_read_mcp_v2(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / 'opencode.json'
            cfg.write_text(json.dumps({'mcp': {'servers': {
                'srv1': {'type': 'remote', 'url': 'https://mcp.example.com/mcp'},
                'srv2': {'type': 'local', 'command': ['npx', 'foo'], 'disabled': True},
            }}}))
            by = {s['name']: s for s in status.read_mcp_servers([cfg])}
            self.assertEqual(by['srv1']['type'], 'remote')
            self.assertEqual(by['srv1']['detail'], 'https://mcp.example.com/mcp')
            self.assertTrue(by['srv2']['disabled'])
            self.assertEqual(by['srv2']['detail'], 'npx foo')

    def test_mcp_ignores_v1_shape(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / 'opencode.json'
            cfg.write_text(json.dumps({'mcp': {'old': {'type': 'local'}}}))
            self.assertEqual(status.read_mcp_servers([cfg]), [])

    def test_read_mcp_missing(self):
        self.assertEqual(status.read_mcp_servers([Path('nope.json')]), [])


class TestStatus(unittest.TestCase):
    def _db(self, updated, idle, pending=0):
        path = Path(tempfile.mkdtemp()) / 'opencode.db'
        con = sqlite3.connect(str(path))
        con.execute('create table session_v2 (id text, time_updated integer, time_idle integer)')
        con.execute('create table session_pending (id text)')
        con.execute('insert into session_v2 values (?,?,?)', ('s1', updated, idle))
        for i in range(pending):
            con.execute('insert into session_pending values (?)', ('p%d' % i,))
        con.commit()
        con.close()
        return path

    def test_busy_when_updated_after_idle(self):
        self.assertEqual(status.read_opencode_status(self._db(2000, 1000))[0], 'busy')

    def test_busy_when_never_idle(self):
        self.assertEqual(status.read_opencode_status(self._db(1000, None))[0], 'busy')

    def test_idle(self):
        self.assertEqual(status.read_opencode_status(self._db(1000, 2000))[0], 'idle')

    def test_pending_wins(self):
        self.assertEqual(status.read_opencode_status(self._db(1000, 2000, pending=1))[0], 'wait')

    def test_off_when_missing(self):
        self.assertEqual(status.read_opencode_status(Path('no_such.db'))[0], 'off')

    def test_none_on_unreadable(self):
        # a directory passed as a db path is unreadable -> None (keep previous)
        self.assertIsNone(status.read_opencode_status(Path(tempfile.mkdtemp())))


@unittest.skipUnless(sys.platform == 'win32', 'Windows only')
class TestOleDrag(unittest.TestCase):
    def test_data_object_for_existing_file(self):
        from quietpet.native import win32
        win32._ensure_ole()
        pdo = win32._make_file_object(Path(__file__).resolve())
        self.assertIsNotNone(pdo)
        if pdo:
            win32._release_com(pdo)

    def test_data_object_exposes_cf_hdrop(self):
        import ctypes
        from ctypes import wintypes
        from quietpet.native import win32

        target = Path(__file__).resolve()
        win32._ensure_ole()
        pdo = win32._make_file_object(target)
        self.assertIsNotNone(pdo)

        fe = win32.FORMATETC(win32.CF_HDROP, None, win32.DVASPECT_CONTENT, -1, win32.TYMED_HGLOBAL)
        med = win32.STGMEDIUM()
        vt = ctypes.cast(pdo, ctypes.POINTER(ctypes.c_void_p))[0]
        funcs = ctypes.cast(vt, ctypes.POINTER(ctypes.c_void_p))
        get_data = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                      ctypes.POINTER(win32.FORMATETC),
                                      ctypes.POINTER(win32.STGMEDIUM))(funcs[3])
        self.assertEqual(get_data(pdo, ctypes.byref(fe), ctypes.byref(med)), 0)
        self.assertEqual(med.tymed, 1)
        shell32 = ctypes.windll.shell32
        shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, ctypes.c_wchar_p, wintypes.UINT]
        shell32.DragQueryFileW.restype = wintypes.UINT
        length = shell32.DragQueryFileW(med.unionmember, 0, None, 0)
        buf = ctypes.create_unicode_buffer(length + 1)
        shell32.DragQueryFileW(med.unionmember, 0, buf, length + 1)
        self.assertEqual(Path(buf.value).name, target.name)
        ctypes.windll.ole32.ReleaseStgMedium(ctypes.byref(med))
        win32._release_com(pdo)

    def test_make_drop_source(self):
        from quietpet.native import win32
        src = win32._make_drop_source()
        self.assertIsNotNone(src)

    def test_text_object_exposes_cf_unicodetext(self):
        import ctypes
        from quietpet.native import win32
        win32._ensure_ole()
        obj = win32._make_text_object('@review')
        ptr = ctypes.cast(ctypes.byref(obj), ctypes.c_void_p)
        vt = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_void_p))[0]
        funcs = ctypes.cast(vt, ctypes.POINTER(ctypes.c_void_p))
        get_data = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                      ctypes.POINTER(win32.FORMATETC),
                                      ctypes.POINTER(win32.STGMEDIUM))(funcs[3])
        fe = win32.FORMATETC(win32.CF_UNICODETEXT, None, win32.DVASPECT_CONTENT, -1, win32.TYMED_HGLOBAL)
        med = win32.STGMEDIUM()
        self.assertEqual(get_data(ptr, ctypes.byref(fe), ctypes.byref(med)), 0)
        kernel32 = ctypes.windll.kernel32
        kernel32.GlobalLock.restype = ctypes.c_void_p
        mem = kernel32.GlobalLock(med.unionmember)
        self.assertEqual(ctypes.wstring_at(mem), '@review')
        kernel32.GlobalUnlock(med.unionmember)
        ctypes.windll.ole32.ReleaseStgMedium(ctypes.byref(med))

    def test_combined_object_offers_text_and_hdrop(self):
        import ctypes
        from quietpet.native import win32
        win32._ensure_ole()
        p = Path(__file__).resolve()
        obj = win32._make_object(text='@x', files=[p])
        ptr = ctypes.cast(ctypes.byref(obj), ctypes.c_void_p)
        vt = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_void_p))[0]
        funcs = ctypes.cast(vt, ctypes.POINTER(ctypes.c_void_p))
        query = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                   ctypes.POINTER(win32.FORMATETC))(funcs[5])
        fe_text = win32.FORMATETC(win32.CF_UNICODETEXT, None, 1, -1, 1)
        fe_file = win32.FORMATETC(win32.CF_HDROP, None, 1, -1, 1)
        self.assertEqual(query(ptr, ctypes.byref(fe_text)), 0)
        self.assertEqual(query(ptr, ctypes.byref(fe_file)), 0)
        get_data = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                      ctypes.POINTER(win32.FORMATETC),
                                      ctypes.POINTER(win32.STGMEDIUM))(funcs[3])
        med = win32.STGMEDIUM()
        self.assertEqual(get_data(ptr, ctypes.byref(fe_file), ctypes.byref(med)), 0)
        shell32 = ctypes.windll.shell32
        shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint]
        shell32.DragQueryFileW.restype = ctypes.c_uint
        length = shell32.DragQueryFileW(med.unionmember, 0, None, 0)
        buf = ctypes.create_unicode_buffer(length + 1)
        shell32.DragQueryFileW(med.unionmember, 0, buf, length + 1)
        self.assertEqual(Path(buf.value).name, p.name)
        ctypes.windll.ole32.ReleaseStgMedium(ctypes.byref(med))

    def test_drag_with_bad_path_is_safe(self):
        from quietpet.native import win32
        win32.start_ole_drag(paths=[str(Path('definitely_missing_xyz'))])  # must not raise


class TestIcons(unittest.TestCase):
    def test_icon_pack_present(self):
        from quietpet.ui import icons
        base = icons.resolve_icon_dir()
        self.assertIsNotNone(base, 'Cursor_QuietPet_Icons should be found')
        self.assertTrue((base / '64px' / 'folder.png').exists())

    def test_decode_png_rgba(self):
        from quietpet.ui import icons
        base = icons.resolve_icon_dir()
        w, h, rgba = icons.decode_png_rgba(base / '64px' / 'folder.png')
        self.assertEqual((w, h), (64, 64))
        self.assertEqual(len(rgba), 64 * 64 * 4)
        alpha = rgba[3::4]
        self.assertTrue(any(a > 0 for a in alpha), 'icon should have opaque pixels')
        self.assertTrue(any(a == 0 for a in alpha), 'icon should have transparent pixels')

    def test_resize_alpha(self):
        from quietpet.ui import icons
        base = icons.resolve_icon_dir()
        w, h, rgba = icons.decode_png_rgba(base / '64px' / 'file.png')
        alpha = icons._resize_alpha(rgba, w, h, 16)
        self.assertEqual(len(alpha), 256)


class TestI18n(unittest.TestCase):
    def tearDown(self):
        from quietpet.core import i18n
        i18n.set_language('zh')

    def test_switch_language(self):
        from quietpet.core import i18n
        i18n.set_language('zh')
        self.assertEqual(i18n.t('tip_new_file'), '新建文件')
        i18n.set_language('en')
        self.assertEqual(i18n.t('tip_new_file'), 'New file')

    def test_unknown_key_falls_back(self):
        from quietpet.core import i18n
        i18n.set_language('zh')
        self.assertEqual(i18n.t('__missing__'), '__missing__')

    def test_format(self):
        from quietpet.core import i18n
        i18n.set_language('en')
        self.assertIn('@x', i18n.t('menu_copy_skill_ref', ref='@x'))

    def test_locale_is_separate_folder(self):
        from quietpet.core import locale
        self.assertTrue(hasattr(locale, 'zh'))
        self.assertTrue(hasattr(locale, 'en'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
