import tempfile
import tkinter as tk
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from quietpet.app import QuietPet
from quietpet.core import config
from quietpet.ui.explorer import Explorer
from quietpet.ui.pet import Pet
from quietpet.ui.tutorial import Tutorial, should_show


class TutorialTests(unittest.TestCase):
    def tearDown(self):
        config.apply_font_size(10)

    def test_first_launch_and_test_replay(self):
        with patch.object(config, 'TUTORIAL_TEST_MODE', False):
            self.assertTrue(should_show({}))
            self.assertFalse(should_show({'tutorial_complete': True}))
        with patch.object(config, 'TUTORIAL_TEST_MODE', True):
            self.assertTrue(should_show({'tutorial_complete': True}))

    def test_complete_skip_replay_and_screen_edges(self):
        root = tk.Tk()
        root.geometry('80x98+0+0')
        settings, save = {}, Mock()
        tutorial = Tutorial(root, settings, save)
        try:
            tutorial.start()
            root.update()
            self.assertGreaterEqual(tutorial.window.winfo_x(), 0)
            self.assertGreaterEqual(tutorial.window.winfo_y(), 0)
            for size in (8, 20):
                config.apply_font_size(size)
                tutorial.render()
                root.update()
                self.assertLessEqual(tutorial.window.winfo_x() + tutorial.window.winfo_width(),
                                     root.winfo_screenwidth())
                self.assertLessEqual(tutorial.window.winfo_y() + tutorial.window.winfo_height(),
                                     root.winfo_screenheight())
            for _ in Tutorial.STEPS:
                tutorial.next()
            self.assertIsNone(tutorial.window)
            self.assertTrue(settings['tutorial_complete'])
            save.assert_called_once()
            tutorial.start()
            self.assertEqual(tutorial.step, 0)
            tutorial.finish()
            self.assertIsNone(tutorial.window)
            pet = object.__new__(Pet)
            pet.canvas = tk.Canvas(root)
            pet.canvas.create_text(20, 20, text='status', tags='status')
            pet.draw_status()
            self.assertEqual(pet.canvas.find_withtag('status'), ())
        finally:
            tutorial.close()
            root.destroy()

    def test_font_change_keeps_selection_and_hidden_panel(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            selected = folder / 'selected.txt'
            selected.write_text('test')
            root = tk.Tk()
            root.withdraw()
            app = object.__new__(QuietPet)
            app.root, app.settings, app.save = root, {'folder': tmp, 'roots': [tmp]}, Mock()
            app.explorer = Explorer(root, app.settings, lambda: (0, 0), app.save)
            app.tutorial = Tutorial(root, app.settings, app.save)
            try:
                app.explorer.show()
                app.explorer.tree.selection_set(str(selected))
                app.explorer.hide()
                for size in (8, 10, 12, 14, 16, 18, 20):
                    app.set_font_size(size)
                    root.update_idletasks()
                    self.assertEqual(app.settings['font_size'], size)
                    self.assertEqual(app.explorer.tree.selection(), (str(selected),))
                    self.assertEqual(app.explorer.panel.state(), 'withdrawn')
                    from tkinter import ttk
                    row = int(ttk.Style(app.explorer.panel).lookup('Quiet.Treeview', 'rowheight'))
                    self.assertGreaterEqual(row, size * 2 + 8)
            finally:
                app.tutorial.close()
                root.destroy()


if __name__ == '__main__':
    unittest.main()
