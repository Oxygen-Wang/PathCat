import tkinter as tk
import unittest
from unittest.mock import Mock

from quietpet.ui.pet import Pet
from quietpet.core.config import IS_WIN


class FileDragCompanionTests(unittest.TestCase):
    def test_missing_empty_hand_sprite_uses_idle_not_old_folder_sprite(self):
        root = tk.Tk()
        pet = Pet(root, {})
        try:
            pet._frames['file_drag'] = []
            pet.follow_file_drag((300, 200))
            self.assertIs(pet._file_drag_image, pet._state_frames('idle')[0])
            pet.follow_file_drag(None)
            self.assertEqual(float(root.attributes('-alpha')), 1)
        finally:
            root.destroy()

    def test_all_missing_images_still_allow_drag_and_restore(self):
        root = tk.Tk()
        pet = Pet(root, {})
        try:
            pet.manifest = {}
            pet._frames.clear()
            pet.follow_file_drag((300, 200))
            self.assertIsNone(pet._file_drag_image)
            canvas = pet._file_drag_window.winfo_children()[0]
            self.assertTrue(canvas.find_withtag('cat'))
            pet.follow_file_drag(None)
            self.assertEqual(float(root.attributes('-alpha')), 1)
        finally:
            root.destroy()

    @unittest.skipUnless(IS_WIN, 'Windows OLE callbacks')
    def test_native_drag_over_uses_value_point_and_notifies_companion(self):
        import ctypes
        from unittest.mock import patch
        from quietpet.native import win32
        follow = Mock()
        effect = ctypes.c_ulong()
        with patch.object(win32, '_target_drag_cb', follow), \
             patch.object(win32, '_target_drag_files', True):
            callback = win32._DT_OVER_FN(win32._t_over)
            callback(None, 0, win32.POINTL(345, 234), ctypes.byref(effect))
        follow.assert_called_once_with((345, 234))
        self.assertEqual(effect.value, win32.DROPEFFECT_COPY)

    def test_follow_and_cancel_restore_pet_without_moving_dock(self):
        root = tk.Tk()
        root.geometry('80x98+40+50')
        root.update_idletasks()
        pet = Pet(root, {})
        root.update_idletasks()
        dock = (root.winfo_x(), root.winfo_y())
        pet.on_moved = Mock()
        try:
            pet.follow_file_drag((300, 200))
            tip = pet._file_drag_window
            self.assertEqual((tip.winfo_x(), tip.winfo_y()), (260, 224))
            self.assertEqual(float(root.attributes('-alpha')), 0)
            pet.follow_file_drag((400, 250))
            self.assertEqual((tip.winfo_x(), tip.winfo_y()), (360, 274))
            self.assertEqual((root.winfo_x(), root.winfo_y()), dock)
            pet.follow_file_drag(None)
            root.update_idletasks()
            self.assertEqual(tip.state(), 'withdrawn')
            self.assertEqual(float(root.attributes('-alpha')), 1)
            pet.on_moved.assert_not_called()
            pet.follow_file_drag(None)
        finally:
            root.destroy()

    def test_near_bottom_puts_companion_above_pointer(self):
        root = tk.Tk()
        pet = Pet(root, {})
        try:
            y = root.winfo_screenheight() - 5
            pet.follow_file_drag((100, y))
            tip = pet._file_drag_window
            self.assertLess(tip.winfo_y() + tip.winfo_height(), y)
            pet.follow_file_drag(None)
        finally:
            root.destroy()
