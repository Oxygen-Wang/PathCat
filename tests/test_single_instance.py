import sys
import unittest
import uuid
from unittest.mock import patch

from quietpet import app
from quietpet.native.instance import SingleInstance


class SingleInstanceTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'win32', 'Windows mutex')
    def test_duplicate_blocked_and_exit_allows_relaunch(self):
        name = 'Local\\PathCat.Test.' + uuid.uuid4().hex
        first, second, third = [SingleInstance(name) for _ in range(3)]
        try:
            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
            first.close()
            self.assertTrue(third.acquire())
        finally:
            for instance in (first, second, third):
                instance.close()

    def test_duplicate_does_not_initialize_gui(self):
        with patch('quietpet.native.instance.SingleInstance') as guard, \
                patch('quietpet.native.instance.notify_running') as notify, \
                patch.object(app, 'QuietPet') as gui:
            guard.return_value.acquire.return_value = False
            app.main()
            gui.assert_not_called()
            notify.assert_called_once()

    def test_guard_released_on_startup_failure(self):
        with patch('quietpet.native.instance.SingleInstance') as guard, \
                patch.object(app, 'QuietPet', side_effect=RuntimeError('startup')):
            guard.return_value.acquire.return_value = True
            with self.assertRaises(RuntimeError):
                app.main()
            guard.return_value.close.assert_called_once()
