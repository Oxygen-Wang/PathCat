import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from quietpet.app import QuietPet
from quietpet.core import config
from quietpet.ui.icons import ICON_NAMES, load_icons
from quietpet.ui.pet import CAT_DIR


class DesktopTests(unittest.TestCase):
    def test_hover_opens_closed_sidebar_and_raises_open_one(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(config, 'load_settings', return_value={'folder': tmp, 'roots': [tmp]}), \
             patch.object(config, 'save_settings'), \
             patch.object(QuietPet, 'start_hotkey'):
            app = QuietPet()
            try:
                app.explorer.show()
                with patch.object(app.explorer.panel, 'lift') as lift, \
                     patch.object(app.explorer.panel, 'focus_force') as focus:
                    app.on_pet_hover()
                    lift.assert_called_once()
                    focus.assert_not_called()
                app.explorer.hide()
                with patch.object(app.explorer.panel, 'lift') as lift, \
                     patch.object(app.explorer, 'show') as show:
                    app.on_pet_hover()
                    lift.assert_not_called()
                    show.assert_called_once_with(activate=False)
            finally:
                app.quit()

    def test_pet_stays_on_top_without_background_focus_raising(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(config, 'load_settings', return_value={'folder': tmp, 'roots': [tmp]}), \
             patch.object(config, 'save_settings'), \
             patch.object(QuietPet, 'start_hotkey'):
            app = QuietPet()
            try:
                app.explorer.show()
                app.root.update_idletasks()
                self.assertTrue(bool(app.root.attributes('-topmost')))
                self.assertTrue(bool(app.explorer.panel.attributes('-topmost')))
                if app.tutorial.window is not None:
                    self.assertFalse(bool(app.tutorial.window.attributes('-topmost')))
                with patch.object(app.pet, 'raise_pet') as raise_pet, \
                     patch.object(app.root, 'lift') as lift:
                    app.dock_pet()
                    app.dock_pet()
                    raise_pet.assert_not_called()
                    lift.assert_not_called()
                self.assertEqual(set(app._timers), {'hotkey', 'dock'})
                self.assertFalse(hasattr(app, 'control'))
                self.assertFalse(hasattr(app, '_control'))
                self.assertFalse(hasattr(app.explorer, 'mcp_config_paths'))
            finally:
                app.quit()
                config.apply_font_size(10)

    def test_all_required_cat_images_and_sidebar_icons_load(self):
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        try:
            manifest = json.loads((CAT_DIR / 'manifest.json').read_text(encoding='utf-8'))
            for state in manifest['states'].values():
                for frame in state['frames']:
                    path = CAT_DIR / frame
                    self.assertTrue(path.is_file(), f'Missing cat frame: {frame}')
                    image = tk.PhotoImage(master=root, file=str(path))
                    self.assertGreater(image.width(), 0)
            self.assertEqual(set(load_icons(root)), set(ICON_NAMES))
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()
