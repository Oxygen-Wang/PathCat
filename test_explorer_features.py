import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from quietpet.core.ignore import is_ignored, transfer_allowed, top_level_paths, escape_pattern
from quietpet.ui.explorer import Explorer


class ExplorerFeatureTests(unittest.TestCase):
    def test_filters_and_literal_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / 'src/node_modules'
            nested.mkdir(parents=True)
            log = root / 'src/run.log'
            log.write_text('log')
            self.assertTrue(is_ignored(nested, root, ['node_modules/']))
            self.assertTrue(is_ignored(nested / 'a.js', root, ['node_modules/']))
            self.assertTrue(is_ignored(log, root, ['*.log']))
            self.assertFalse(is_ignored(log, root, ['*.log/']))
            self.assertFalse(is_ignored(nested, root, ['/node_modules/']))
            literal = root / 'a[1].txt'
            rule = '/' + escape_pattern(literal.name)
            self.assertTrue(is_ignored(literal, root, [rule]))
            self.assertFalse(is_ignored(root / 'a1.txt', root, [rule]))
            self.assertFalse(is_ignored(log, root, ['# comment', '']))

    def test_project_persistence_and_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = object.__new__(Explorer)
            app.settings = {}
            app.folder = Path(tmp) / 'one'
            app.folder.mkdir()
            app.save = Mock()
            app.rebuild = Mock()
            app.selected_paths = Mock(return_value=[app.folder / 'a[1].txt'])
            app.ignore_selection()
            saved = dict(app.settings)
            self.assertTrue(is_ignored(app.folder / 'a[1].txt', app.folder, app.ignore_patterns()))
            app.folder = Path(tmp) / 'two'
            self.assertFalse(is_ignored(app.folder / 'a[1].txt', app.folder, app.ignore_patterns()))
            app.folder = Path(tmp) / 'one'
            app.settings = saved
            app.set_ignore_patterns([])
            self.assertFalse(is_ignored(app.folder / 'a[1].txt', app.folder, app.ignore_patterns()))

    def test_recursive_and_duplicate_transfers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            child = source / 'child'
            child.mkdir(parents=True)
            file = child / 'file.txt'
            file.write_text('original')
            self.assertFalse(transfer_allowed(source, child))
            self.assertFalse(transfer_allowed(source, source))
            self.assertTrue(transfer_allowed(file, source))
            self.assertEqual(top_level_paths([file, source, file]), [source])
            app = object.__new__(Explorer)
            app._copy_path(source, child)
            app._move_path(source, child)
            self.assertFalse((child / 'source').exists())
            self.assertEqual(file.read_text(), 'original')

    def test_click_does_not_move_file(self):
        app = object.__new__(Explorer)
        app._drag_moved = False
        app._press_xy = (100, 100)
        app._cancel_watch = Mock()
        app._drag_items = [Path('file.txt')]
        app._drag_active = True
        app._press_iid = 'file.txt'
        app.tree = Mock()
        app.drag_end(SimpleNamespace(x_root=100, y_root=100, y=10, state=0))
        app.tree.identify_row.assert_not_called()

    def test_drag_move_and_ctrl_copy(self):
        for copy in (False, True):
            with self.subTest(copy=copy), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / 'file.txt'
                source.write_text('payload')
                destination = root / 'destination'
                destination.mkdir()
                app = object.__new__(Explorer)
                app.folder = root
                app._drag_moved = True
                app._press_xy = (0, 0)
                app._cancel_watch = Mock()
                app._drag_items = [source]
                app._drag_active = True
                app._press_iid = str(source)
                app.tree = Mock()
                app.tree.identify_row.return_value = str(destination)
                app._drop_destination = Mock(return_value=destination)
                app._root_at = Mock(return_value=None)
                app._expand_to = Mock()
                app.on_event = Mock()
                app.rebuild = Mock()
                app.drag_end(SimpleNamespace(x_root=20, y_root=20, y=20,
                                             state=4 if copy else 0))
                self.assertEqual((destination / source.name).read_text(), 'payload')
                self.assertEqual(source.exists(), copy)

    def test_tree_filters_including_temporary_show(self):
        import tkinter as tk
        from tkinter import ttk
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'node_modules').mkdir()
            (root / '.gitignore').write_text('node_modules/\n')
            (root / 'keep.txt').write_text('visible')
            window = tk.Tk()
            window.withdraw()
            try:
                app = object.__new__(Explorer)
                app.folder = root
                app.settings = {}
                app.icons = {}
                app.show_ignored = False
                app.tree = ttk.Treeview(window)
                app._populate('', root)
                self.assertFalse(app.tree.exists(str(root / 'node_modules')))
                self.assertTrue(app.tree.exists(str(root / 'keep.txt')))
                app.show_ignored = True
                app._populate('', root)
                self.assertTrue(app.tree.exists(str(root / 'node_modules')))
            finally:
                window.destroy()


if __name__ == '__main__':
    unittest.main()
