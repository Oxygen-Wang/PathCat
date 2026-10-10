import time
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from quietpet.app import QuietPet
from quietpet.core import config
from quietpet.ui.pet import Pet


class HoverDelayTests(unittest.TestCase):
    def test_brief_hover_and_click_cancel_pending_open(self):
        root = tk.Tk()
        pet = Pet(root, {})
        pet.on_hover = Mock()
        try:
            pet._enter()
            pending = pet._hover_after
            self.assertIsNotNone(pending)
            pet.on_hover.assert_not_called()
            pet._leave()
            self.assertIsNone(pet._hover_after)
            self.assertNotIn(pending, root.tk.splitlist(root.tk.call('after', 'info')))
            pet._enter()
            pet._down(Mock(x_root=10, y_root=10))
            self.assertIsNone(pet._hover_after)
            pet._hover_open()
            pet.on_hover.assert_not_called()
        finally:
            root.destroy()


class SidebarInteractionTests(unittest.TestCase):
    def test_startup_is_quiet_and_hover_panel_can_receive_keyboard(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(config, 'load_settings', return_value={'folder': folder, 'roots': [folder]}), \
             patch.object(config, 'save_settings'), \
             patch.object(QuietPet, 'start_hotkey'):
            for name in ('a.txt', 'b.txt'):
                (Path(folder) / name).write_text('example')
            app = QuietPet()
            try:
                app.root.update()
                self.assertIsNone(app.tutorial.window)
                self.assertFalse(app._panel_visible())
                app.on_pet_hover()
                app.root.update()
                self.assertTrue(app._panel_visible())
                self.assertFalse(app.explorer.panel.overrideredirect())
                # Explicit opening activates the file tree for keyboard actions.
                app.explorer.show()
                app.root.update()
                tree = app.explorer.tree
                self.assertIs(app.root.focus_get(), tree)
                first, second = tree.get_children('')
                tree.focus(first)
                tree.selection_set(first)
                tree.event_generate('<Down>')
                app.root.update()
                self.assertEqual(tree.selection(), (second,))
                app.pet._leave()
                self.assertTrue(app._panel_visible())
                app.explorer.hide()
                self.assertFalse(app._panel_visible())
                self.assertTrue(app.root.winfo_exists())
            finally:
                app.quit()

    def test_panel_edge_resize_is_saved_and_cat_follows_both_sides(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(config, 'load_settings', return_value={'folder': folder, 'roots': [folder]}), \
             patch.object(config, 'save_settings') as save, \
             patch.object(QuietPet, 'start_hotkey'):
            app = QuietPet()
            try:
                app.explorer.show()
                app.root.update()
                for side, width in [('right', 420), ('left', 380)]:
                    app.settings['panel_side'] = side
                    app.explorer.position()
                    app.root.update()
                    app.explorer.panel.geometry(f'{width}x600')
                    app.root.update()
                    deadline = time.monotonic() + 2
                    while app.explorer._resize_after and time.monotonic() < deadline:
                        time.sleep(.01)
                        app.root.update()
                    self.assertEqual(app.settings['panel_width'], width)
                    self.assertEqual(app.explorer.panel.winfo_width(), width)
                    self.assertEqual(app.root.winfo_x(), app._cat_x_for_state())
                    self.assertIsNone(app.explorer._resize_after)
                    app.explorer.hide()
                    app.explorer.show(activate=False)
                    app.root.update()
                    self.assertEqual(app.explorer.panel.winfo_width(), width)
                save.assert_called()
            finally:
                app.quit()
