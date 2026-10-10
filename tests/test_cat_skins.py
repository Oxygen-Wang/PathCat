import tkinter as tk
import unittest
from unittest.mock import patch

from quietpet.ui.pet import Pet


class CatSkinTests(unittest.TestCase):
    def test_calico_loads_drag_sleep_skill_and_falls_back_for_missing_art(self):
        root = tk.Tk()
        pet = Pet(root, {})
        try:
            pet.set_skin('calico')
            self.assertEqual(pet.settings['cat_skin'], 'calico')
            self.assertEqual(pet._state_frames('file_drag')[0].width(), 64)
            self.assertTrue(pet._state_frames('sleeping'))
            self.assertTrue(pet._state_frames('skill_drag'))
            pet.manifest['missing_art'] = {'frames': []}
            self.assertIs(pet._display_frames('missing_art')[0], pet._state_frames('idle')[0])
            pet.follow_file_drag((300, 200))
            self.assertIs(pet._file_drag_image, pet._state_frames('file_drag')[0])
            pet.set_skin('default')
            self.assertIsNone(pet._file_drag_window)
            self.assertEqual(float(root.attributes('-alpha')), 1)
            self.assertEqual(pet.skin, 'default')
        finally:
            root.destroy()

    def test_saved_skin_loads_on_startup(self):
        root = tk.Tk()
        try:
            pet = Pet(root, {'cat_skin': 'calico'})
            self.assertEqual(pet.skin, 'calico')
            self.assertTrue(pet._state_frames('idle'))
            for name in pet.manifest:
                self.assertTrue(pet._display_frames(name))
        finally:
            root.destroy()

    def test_fourth_batch_poses_load_at_all_sizes_and_sleep_uses_new_art(self):
        root = tk.Tk()
        pet = Pet(root, {'cat_skin': 'calico'})
        try:
            for scale in (75, 100, 150, 200):
                pet.set_scale(scale)
                for state in ('angry', 'tired', 'sleeping', 'stretch', 'groom',
                              'eat', 'music', 'peek', 'jump', 'run'):
                    frames = pet._state_frames(state)
                    self.assertTrue(frames, state)
                    self.assertEqual(frames[0].width(), round(64 * scale / 100))
            with patch('quietpet.ui.pet.time.monotonic', return_value=pet._last_activity + 301):
                pet.check_inactivity()
            self.assertTrue(pet.sleeping)
            self.assertEqual(pet.state, 'sleeping')
            self.assertIs(pet._display_frames('sleeping')[0], pet._state_frames('sleeping')[0])
            pet.note_activity()
            self.assertFalse(pet.sleeping)
        finally:
            root.destroy()
