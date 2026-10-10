import ctypes
import sys
import tkinter as tk
import unittest
from unittest.mock import Mock, patch

from quietpet.native.tray import TrayIcon


@unittest.skipUnless(sys.platform == 'win32', 'Windows notification area')
class TrayTests(unittest.TestCase):
    def test_unavailable_notification_area_retries_without_stopping_app(self):
        root = tk.Tk()
        root.withdraw()
        tray = None
        try:
            with patch.object(TrayIcon, '_add_to_shell'):
                tray = TrayIcon(root, Mock(), Mock(), lambda: ('Show', 'Quit'))
            self.assertFalse(tray.added)
            self.assertIsNotNone(tray.hwnd)
            self.assertIsNotNone(tray._retry_after)
            root.update()
            # Once Explorer recovers, an already-scheduled retry can add it.
            def recover():
                tray.added = True
            root.after_cancel(tray._retry_after)
            with patch.object(tray, '_add_to_shell', side_effect=recover):
                tray._retry()
            self.assertTrue(tray.added)
            self.assertIsNone(tray._retry_after)
        finally:
            if tray is not None:
                # The mocked recovery did not actually add an icon.
                tray.added = False
                tray.close()
            root.destroy()

    def test_native_initialization_failure_is_nonfatal(self):
        root = tk.Tk()
        try:
            with patch.object(TrayIcon, '_create', side_effect=OSError('tray unavailable')):
                tray = TrayIcon(root, Mock(), Mock(), lambda: ('Show', 'Quit'))
            self.assertEqual(tray.startup_error, 'tray unavailable')
            self.assertFalse(tray.added)
            tray.close()
            self.assertTrue(root.winfo_exists())
        finally:
            root.destroy()

    def test_close_cancels_notification_area_retry(self):
        root = tk.Tk()
        tray = None
        try:
            with patch.object(TrayIcon, '_add_to_shell'):
                tray = TrayIcon(root, Mock(), Mock(), lambda: ('Show', 'Quit'))
            retry = tray._retry_after
            tray.close()
            self.assertIsNone(tray._retry_after)
            self.assertNotIn(retry, root.tk.splitlist(root.tk.call('after', 'info')))
            tray._retry()
            self.assertIsNone(tray.hwnd)
        finally:
            if tray is not None:
                tray.close()
            root.destroy()

    def test_icon_callbacks_restart_and_cleanup(self):
        root = tk.Tk()
        root.withdraw()
        show, quit_app = Mock(), Mock()
        tray = None
        try:
            tray = TrayIcon(root, show, quit_app, lambda: ('打开侧栏', '退出 PathCat'))
            self.assertTrue(tray.added)
            hwnd, icon = tray.hwnd, tray.icon
            tray._message(hwnd, tray.CALLBACK, 1, 0x202)
            show.assert_not_called()
            root.after_cancel(tray._poll_after)
            tray._poll_events()
            show.assert_called_once()
            quit_app.assert_not_called()
            tray.menu = Mock()
            tray._message(hwnd, tray.CALLBACK, 1, 0x205)
            root.after_cancel(tray._poll_after)
            tray._poll_events()
            tray.menu.assert_called_once()
            # Exercise both native menu commands without blocking for a click.
            del tray.menu
            user = tray.user
            try:
                tray.user = Mock()
                tray.user.TrackPopupMenu.return_value = 1
                tray.menu()
                self.assertEqual(show.call_count, 2)
                tray.user.TrackPopupMenu.return_value = 2
                tray.menu()
                quit_app.assert_called_once()
                self.assertEqual(tray.user.DestroyMenu.call_count, 2)
            finally:
                tray.user = user
            # Simulate Explorer replacing the notification area.
            self.assertTrue(tray.shell.Shell_NotifyIconW(2, ctypes.byref(tray.data)))
            tray._message(hwnd, tray.restart_message, 0, 0)
            root.after_cancel(tray._poll_after)
            tray._poll_events()
            self.assertTrue(tray.added)
            tray.close()
            self.assertIsNone(tray.hwnd)
            self.assertIsNone(tray.icon)
            self.assertFalse(tray.added)
            tray.close()
        finally:
            if tray is not None:
                tray.close()
            root.destroy()
