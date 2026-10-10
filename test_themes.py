import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from quietpet.core import config
from quietpet.core.themes import initialize_settings, PALETTES
from quietpet.ui.explorer import Explorer
from quietpet.ui.pet import Pet


class ThemeTests(unittest.TestCase):
    def tearDown(self):
        config.apply_theme('dark')

    def test_existing_shortcut_migrates_only_once(self):
        settings = {'hotkey': 'Alt'}
        initialize_settings(settings)
        self.assertEqual(settings['hotkey'], 'Ctrl+B')
        settings['hotkey'] = 'Ctrl+Alt+Q'
        initialize_settings(settings)
        self.assertEqual(settings['hotkey'], 'Ctrl+Alt+Q')

    def test_all_palettes_and_panel_recreation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / 'selected.txt').write_text('test')
            window = tk.Tk()
            window.withdraw()
            ex = Explorer(window, {'folder': str(folder), 'roots': [str(folder)]}, lambda: (0, 0), Mock())
            try:
                ex.show()
                iid = str(folder / 'selected.txt')
                ex.tree.selection_set(iid)
                for name in PALETTES:
                    config.apply_theme(name)
                    ex.recreate()
                    self.assertEqual(ex.panel.cget('background'), config.BG)
                    self.assertEqual(ex.tree.selection(), (iid,))
                    self.assertEqual(ex.panel.state(), 'normal')
                ex.hide()
                ex.recreate()
                self.assertEqual(ex.panel.state(), 'withdrawn')
            finally:
                if ex.panel:
                    ex.panel.destroy()
                window.destroy()


if __name__ == '__main__':
    unittest.main()
