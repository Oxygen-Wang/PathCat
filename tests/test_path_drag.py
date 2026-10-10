import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from quietpet.ui.explorer import Explorer


class PathDragTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.first = Path(self.temp.name) / 'one'
        self.second = Path(self.temp.name) / 'two'
        self.first.mkdir()
        self.second.mkdir()
        self.source = self.first / 'payload.txt'
        self.source.write_text('payload', encoding='utf-8')
        self.root = tk.Tk()
        self.root.withdraw()
        self.ex = Explorer(self.root, {'folder': str(self.first),
                                      'roots': [str(self.first), str(self.second)]},
                           lambda: (0, 0), Mock())
        self.ex.show()
        self.root.update_idletasks()

    def tearDown(self):
        self.ex._cancel_watch()
        self.root.destroy()
        self.temp.cleanup()

    def begin(self):
        self.ex.tree.selection_set(str(self.source))
        box = self.ex.tree.bbox(str(self.source))
        x, y = self.ex.tree.winfo_rootx() + 40, self.ex.tree.winfo_rooty() + box[1] + 5
        self.ex.drag_start(SimpleNamespace(x_root=x, y_root=y, y=box[1] + 5))

    def tab_point(self):
        chip = self.ex._root_chips[str(self.second)]
        return chip.winfo_rootx() + 5, chip.winfo_rooty() + 5

    def test_file_companion_follows_and_cancels_with_drag(self):
        follow = self.ex.on_file_drag = Mock()
        self.begin()
        self.ex.tree.after_cancel(self.ex._watch_after)
        self.ex._watch_after = None
        x, y = self.tab_point()
        with patch('quietpet.ui.explorer.get_cursor_pos', return_value=(x, y)), \
             patch('quietpet.ui.explorer.left_button_down', return_value=True):
            self.ex._watch_external_drag()
        follow.assert_called_with((x, y))
        self.ex.cancel_drag()
        follow.assert_called_with(None)
        self.assertTrue(self.source.exists())

    def test_native_drag_failure_always_hides_companion(self):
        follow = self.ex.on_file_drag = Mock()
        self.begin()
        self.ex.tree.after_cancel(self.ex._watch_after)
        self.ex._watch_after = None
        with patch('quietpet.ui.explorer.get_cursor_pos', return_value=(-100, -100)), \
             patch('quietpet.ui.explorer.left_button_down', return_value=True), \
             patch('quietpet.ui.explorer.start_ole_drag', side_effect=RuntimeError('drag failed')):
            with self.assertRaises(RuntimeError):
                self.ex._watch_external_drag()
        follow.assert_called_with(None)
        self.assertTrue(self.source.exists())

    def test_direct_cross_path_move_and_select_destination(self):
        self.begin()
        x, y = self.tab_point()
        self.ex.drag_end(SimpleNamespace(x_root=x, y_root=y, state=0))
        moved = self.second / self.source.name
        self.assertFalse(self.source.exists())
        self.assertEqual(moved.read_text(), 'payload')
        self.assertEqual(self.ex.folder, self.second)
        self.assertEqual(self.ex.tree.selection(), (str(moved),))

    def test_hover_switch_then_ctrl_copy_into_nested_folder(self):
        nested = self.second / 'nested'
        nested.mkdir()
        self.begin()
        x, y = self.tab_point()
        self.ex._drag_root = str(self.second)
        self.ex._drag_root_since = 0
        self.ex.tree.after_cancel(self.ex._watch_after)
        self.ex._watch_after = None
        with patch('quietpet.ui.explorer.get_cursor_pos', return_value=(x, y)), \
             patch('quietpet.ui.explorer.left_button_down', return_value=True):
            self.ex._watch_external_drag()
        self.assertEqual(self.ex.folder, self.second)
        self.assertEqual(self.ex._drag_items, [self.source])
        self.assertIsNotNone(self.ex._drag_preview)
        self.root.update_idletasks()
        box = self.ex.tree.bbox(str(nested))
        x = self.ex.tree.winfo_rootx() + 40
        y = self.ex.tree.winfo_rooty() + box[1] + 5
        self.ex.drag_end(SimpleNamespace(x_root=x, y_root=y, state=4))
        self.assertTrue(self.source.exists())
        self.assertEqual((nested / self.source.name).read_text(), 'payload')
        self.assertIsNone(self.ex._drag_preview)

    def test_toolbar_release_does_not_move_and_escape_cancels(self):
        self.begin()
        x, y = self.ex.panel.winfo_rootx() + 10, self.ex.tree.winfo_rooty() - 5
        self.ex.drag_end(SimpleNamespace(x_root=x, y_root=y, state=0))
        self.assertTrue(self.source.exists())
        self.begin()
        self.assertEqual(self.ex.cancel_drag(), 'break')
        x, y = self.tab_point()
        self.ex.drag_end(SimpleNamespace(x_root=x, y_root=y, state=0))
        self.assertTrue(self.source.exists())

    def test_native_drop_to_another_managed_path_moves(self):
        self.ex._on_panel_drop([str(self.source)], False, self.tab_point())
        self.assertFalse(self.source.exists())
        self.assertTrue((self.second / self.source.name).exists())

    def test_cross_path_collision_keeps_both_files(self):
        existing = self.second / self.source.name
        existing.write_text('existing')
        self.begin()
        x, y = self.tab_point()
        self.ex.drag_end(SimpleNamespace(x_root=x, y_root=y, state=0))
        self.assertEqual(existing.read_text(), 'existing')
        self.assertEqual(sorted(p.read_text() for p in self.second.iterdir()),
                         ['existing', 'payload'])
        self.assertFalse(self.source.exists())


if __name__ == '__main__':
    unittest.main()
