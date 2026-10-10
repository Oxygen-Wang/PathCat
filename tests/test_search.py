import tempfile
import threading
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import Mock

from quietpet.core import config
from quietpet.core.search import find_paths
from quietpet.ui.explorer import Explorer
from quietpet.ui.pet import Pet


class SearchTests(unittest.TestCase):
    def test_recursive_casefold_ignore_and_cancel(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'nested').mkdir()
            (root / 'nested/Report.TXT').write_text('a')
            (root / 'ReportFolder').mkdir()
            (root / 'hidden').mkdir()
            (root / 'hidden/report.txt').write_text('b')
            (root / config.TRASH).mkdir()
            (root / config.TRASH / 'report.txt').write_text('c')
            (root / '.cursorignore').write_text('hidden/')
            cancel = threading.Event()
            result = set(find_paths(root, 'REPORT', cancel))
            self.assertEqual(result, {root / 'nested/Report.TXT', root / 'ReportFolder'})
            self.assertIn(root / 'hidden/report.txt', set(find_paths(root, 'report', cancel, True)))
            cancel.set()
            self.assertEqual(list(find_paths(root, 'report', cancel)), [])

    def test_search_results_open_files_clear_and_cancel_stale_results(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / 'child').mkdir()
            target = path / 'child/报告.txt'
            target.write_text('a')
            root = tk.Tk()
            explorer = Explorer(root, {'folder': folder}, lambda: (0, 0), Mock())
            try:
                explorer.show()
                self.assertIn('search', explorer.icons)
                root.update_idletasks()
                self.assertFalse(explorer.search_bar.winfo_ismapped())
                explorer.focus_search()
                root.update_idletasks()
                self.assertTrue(explorer.search_bar.winfo_ismapped())
                self.assertTrue(bool(explorer.panel.attributes('-topmost')))
                explorer.search_var.set('报告')
                explorer._search_now()
                deadline = time.monotonic() + 3
                while explorer._search_after and time.monotonic() < deadline:
                    root.update()
                    time.sleep(.01)
                self.assertEqual(explorer.tree.get_children(), (str(target),))
                self.assertEqual(explorer.tree.item(str(target), 'text'), 'child/报告.txt')
                explorer._open_external = Mock()
                explorer.activate(str(target))
                explorer._open_external.assert_called_once_with(target)
                explorer.search_var.set('not-found')
                explorer._search_now()
                cancelled = explorer._search_cancel
                explorer.clear_search()
                self.assertTrue(cancelled.is_set())
                root.update()
                self.assertIn(str(path / 'child'), explorer.tree.get_children())
                self.assertEqual(explorer.search_var.get(), '')
                root.update_idletasks()
                self.assertFalse(explorer.search_bar.winfo_ismapped())
            finally:
                explorer._cancel_search()
                root.destroy()

    def test_hide_cancels_search_and_reopens_normal_file_tree(self):
        with tempfile.TemporaryDirectory() as folder:
            child = Path(folder) / 'child'
            child.mkdir()
            root = tk.Tk()
            explorer = Explorer(root, {'folder': folder}, lambda: (0, 0), Mock())
            try:
                explorer.show()
                explorer.focus_search()
                explorer.search_var.set('missing')
                explorer._search_now()
                cancelled = explorer._search_cancel
                explorer.hide()
                self.assertTrue(cancelled.is_set())
                self.assertEqual(explorer.search_var.get(), '')
                self.assertFalse(explorer._search_visible)
                explorer.show(activate=False)
                root.update()
                self.assertFalse(explorer.search_bar.winfo_ismapped())
                self.assertIn(str(child), explorer.tree.get_children())
                self.assertIsNone(explorer._search_after)
            finally:
                explorer._cancel_search()
                explorer._cancel_skills_layout()
                root.destroy()

    def test_third_batch_states_have_artwork(self):
        root = tk.Tk()
        try:
            pet = Pet(root, {'cat_skin': 'calico'})
            for state in ('wave', 'error', 'confused', 'shy', 'success', 'happy',
                          'sad', 'excited', 'offline', 'talk'):
                self.assertTrue(pet._state_frames(state), state)
        finally:
            root.destroy()
