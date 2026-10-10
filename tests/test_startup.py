import subprocess
import sys
import unittest
from pathlib import Path


@unittest.skipUnless(sys.platform == 'win32', 'Windows desktop startup')
class StartupTests(unittest.TestCase):
    def test_native_tray_right_click_is_processed_by_tk_poll(self):
        script = '''
import tkinter as tk
from unittest.mock import Mock
from quietpet.native.tray import TrayIcon
root = tk.Tk()
root.withdraw()
tray = TrayIcon(root, Mock(), Mock(), lambda: ('Show', 'Quit'))
tray.menu = Mock()
root.after(100, lambda: tray.user.PostMessageW(tray.hwnd, tray.CALLBACK, 1, 0x205))
root.after(350, root.quit)
root.mainloop()
assert tray.menu.call_count == 1, tray.menu.call_count
tray.close()
root.destroy()
print('clean exit')
'''
        self._run_script(script)

    def test_desktop_cat_right_click_menu_does_not_crash(self):
        script = '''
import tempfile
import tkinter as tk
from unittest.mock import patch
from quietpet.app import QuietPet
from quietpet.core import config
with tempfile.TemporaryDirectory(dir='.test-tmp') as folder:
    with patch.object(config, 'load_settings', return_value={'folder': folder, 'roots': [folder]}), patch.object(config, 'save_settings'), patch.object(QuietPet, 'start_hotkey'):
        app = QuietPet()
        def close_menus():
            import ctypes
            menus = [w for w in app.root.winfo_children() if isinstance(w, tk.Menu)]
            assert menus, 'Right-click did not open menu'
            ctypes.windll.user32.EndMenu()
            for menu in menus:
                menu.unpost()
                menu.grab_release()
        app.root.after(150, lambda: app.pet.canvas.event_generate('<Button-3>', x=40, y=50))
        app.root.after(400, close_menus)
        app.root.after(700, app.quit)
        app.run()
print('clean exit')
'''
        self._run_script(script)

    def test_real_mainloop_with_drop_targets_does_not_crash(self):
        # update() alone missed a fatal interaction between a replaced Tk
        # window procedure and mainloop's Python thread-state handling.
        script = '''
import tempfile
from unittest.mock import patch
from quietpet.app import QuietPet
from quietpet.core import config
with tempfile.TemporaryDirectory(dir='.test-tmp') as folder:
    with patch.object(config, 'load_settings', return_value={'folder': folder, 'roots': [folder]}), patch.object(config, 'save_settings'), patch.object(QuietPet, 'start_hotkey'):
        app = QuietPet()
        app.root.after(1200, app.quit)
        app.run()
print('clean exit')
'''
        self._run_script(script)

    def _run_script(self, script):
        workspace = Path(__file__).resolve().parents[1]
        (workspace / '.test-tmp').mkdir(exist_ok=True)
        result = subprocess.run([sys.executable, '-c', script], cwd=workspace,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('clean exit', result.stdout)
