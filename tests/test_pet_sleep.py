import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from quietpet.app import QuietPet
from quietpet.core import config
from quietpet.ui.pet import IDLE_SLEEP_SECONDS, Pet


class PetSleepTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.pet = Pet(self.root, {})
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_sleep_after_five_minutes_and_stay_visible(self):
        self.pet._last_activity = 0
        self.pet.play('happy')
        self.pet._last_activity = 0
        with patch('quietpet.ui.pet.time.monotonic', return_value=IDLE_SLEEP_SECONDS - 1):
            self.pet.check_inactivity()
        self.assertFalse(self.pet.sleeping)
        with patch('quietpet.ui.pet.time.monotonic', return_value=IDLE_SLEEP_SECONDS):
            self.pet.check_inactivity()
        self.assertTrue(self.pet.sleeping)
        self.assertEqual(self.pet.state, 'sleeping')
        self.assertEqual(self.pet.base_state, 'sleeping')
        self.assertIsNone(self.pet._revert_after)
        self.assertEqual(float(self.root.attributes('-alpha')), 1)
        self.assertTrue(bool(self.root.attributes('-topmost')))

    def test_interaction_wakes_and_restarts_timeout(self):
        self.pet.base_state = 'waiting'
        self.pet._last_activity = 0
        with patch('quietpet.ui.pet.time.monotonic', return_value=400):
            self.pet.check_inactivity()
        with patch('quietpet.ui.pet.time.monotonic', return_value=410):
            self.pet.note_activity()
        self.assertFalse(self.pet.sleeping)
        self.assertEqual(self.pet.state, 'waiting')
        with patch('quietpet.ui.pet.time.monotonic', return_value=709):
            self.pet.check_inactivity()
        self.assertFalse(self.pet.sleeping)

    def test_do_not_sleep_during_drag(self):
        self.pet._last_activity = 0
        with patch('quietpet.ui.pet.time.monotonic', return_value=400):
            self.pet.drag_start = (1, 2, 3, 4)
            self.pet.check_inactivity()
            self.assertFalse(self.pet.sleeping)
            self.pet.drag_start = None
            self.pet._file_drag_alpha = 1
            self.pet.check_inactivity()
            self.assertFalse(self.pet.sleeping)


class WakeHotkeyTests(unittest.TestCase):
    def test_hotkey_wakes_restores_visibility_and_opens_sidebar(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(config, 'load_settings', return_value={'folder': folder, 'roots': [folder]}), \
             patch.object(config, 'save_settings'), \
             patch.object(QuietPet, 'start_hotkey'):
            app = QuietPet()
            try:
                app.pet._last_activity = 0
                with patch('quietpet.ui.pet.time.monotonic', return_value=400):
                    app.pet.check_inactivity()
                self.assertTrue(app.pet.sleeping)
                app.root.withdraw()
                app.root.attributes('-alpha', 0)
                app.pet._file_drag_alpha = 1
                app.on_hotkey()
                app.root.update_idletasks()
                self.assertFalse(app.pet.sleeping)
                self.assertEqual(app.pet.base_state, 'idle')
                self.assertEqual(app.root.state(), 'normal')
                self.assertEqual(float(app.root.attributes('-alpha')), 1)
                self.assertTrue(bool(app.root.attributes('-topmost')))
                self.assertTrue(app._panel_visible())
            finally:
                app.quit()
