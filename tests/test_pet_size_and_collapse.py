import os
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from quietpet.app import QuietPet
from quietpet.core import config
from quietpet.ui.pet import Pet
from quietpet.ui.pet_images import encode_rgba, load_pet_image


class PetSizeTests(unittest.TestCase):
    def test_resize_updates_art_window_and_drag_companion(self):
        root = tk.Tk()
        settings = {'cat_skin': 'calico'}
        pet = Pet(root, settings)
        try:
            for scale in (75, 150, 200, 100):
                pet.set_scale(scale)
                root.update_idletasks()
                self.assertEqual((root.winfo_width(), root.winfo_height()), pet.window_size)
                self.assertEqual(pet._display_frames('idle')[0].width(), round(64 * scale / 100))
                self.assertEqual(settings['cat_scale'], scale)
                pet.follow_file_drag((300, 200))
                root.update_idletasks()
                self.assertEqual(pet._file_drag_window.winfo_width(), pet.window_size[0])
                pet.follow_file_drag(None)
        finally:
            root.destroy()

    def test_partial_alpha_never_blends_with_pink_background(self):
        root = tk.Tk()
        try:
            with tempfile.TemporaryDirectory() as folder:
                image_path = Path(folder) / 'fur.png'
                image_path.write_bytes(encode_rgba(2, 1, bytes([180, 120, 60, 160, 10, 20, 30, 0])))
                image = load_pet_image(root, image_path)
                self.assertEqual(image.get(0, 0), (180, 120, 60))
                self.assertFalse(image.transparency_get(0, 0))
                self.assertTrue(image.transparency_get(63, 0))
        finally:
            root.destroy()


class SidebarCollapseTests(unittest.TestCase):
    def test_switching_apps_collapses_but_hover_and_drags_stay_open(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(config, 'load_settings', return_value={'folder': folder, 'roots': [folder]}), \
             patch.object(config, 'save_settings'), \
             patch.object(QuietPet, 'start_hotkey'), \
             patch('quietpet.native.win32.foreground_process_id', return_value=1234) as foreground:
            app = QuietPet()
            try:
                app.on_pet_hover()
                app.check_sidebar_foreground()
                self.assertTrue(app._panel_visible())
                foreground.return_value = os.getpid()
                app.check_sidebar_foreground()
                self.assertTrue(app._panel_visible())
                foreground.return_value = 5678
                app.explorer._drag_active = True
                app.check_sidebar_foreground()
                self.assertTrue(app._panel_visible())
                app.explorer._drag_active = False
                app.check_sidebar_foreground()
                self.assertFalse(app._panel_visible())
                self.assertTrue(app.root.winfo_exists())
                app.on_pet_hover()
                foreground.return_value = 9012
                app.check_sidebar_foreground()
                self.assertFalse(app._panel_visible())
            finally:
                app.quit()
