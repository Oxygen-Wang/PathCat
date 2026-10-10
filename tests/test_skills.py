import tempfile
import threading
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from quietpet.core import config
from quietpet.core.skills import list_open_skills
from quietpet.ui.explorer import Explorer


class SkillRestoreTests(unittest.TestCase):
    def test_project_skill_overrides_global_and_reads_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            global_source = root / 'global'
            project = root / 'project'
            for directory, name in [(global_source / 'example', 'Global'),
                                    (project / '.agents/skills/example', 'Project')]:
                directory.mkdir(parents=True)
                (directory / 'SKILL.md').write_text(f'---\nname: {name}\ndescription: Example skill\n---\nBody')
            with patch('quietpet.core.skills.GLOBAL_SKILL_SOURCES', [global_source]):
                skills = list_open_skills(project, config_paths=[])
            self.assertEqual(len(skills), 1)
            self.assertEqual(skills[0]['name'], 'Project')
            self.assertEqual(skills[0]['description'], 'Example skill')

    def test_skill_dock_survives_search_click_copies_drag_carries_document(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'SKILL.md'
            path.write_text('body')
            skill = {'id': 'example', 'name': 'Example', 'path': path, 'description': 'Description'}
            root = tk.Tk()
            explorer = Explorer(root, {'folder': folder}, lambda: (0, 0), Mock())
            try:
                with patch('quietpet.ui.explorer.list_open_skills', return_value=[skill]):
                    explorer.show()
                    root.update_idletasks()
                    self.assertTrue(explorer.skills_area.winfo_ismapped())
                    self.assertIn('(1)', explorer.skills_header.cget('text'))
                    explorer.copy_text = Mock()
                    explorer._start_watch = Mock()
                    explorer._chip_press(SimpleNamespace(x_root=10, y_root=20), skill)
                    self.assertEqual(explorer._drag_items, [path])
                    explorer._chip_release(SimpleNamespace())
                    explorer.copy_text.assert_called_once_with('@example')
                    self.assertEqual(explorer.settings['skill_usage']['example'], 1)
                    explorer.search_var.set('missing')
                    explorer._search_now()
                    root.update_idletasks()
                    self.assertTrue(explorer.skills_area.winfo_ismapped())
                    self.assertEqual(explorer._skills[0]['id'], 'example')
                    explorer.clear_search()
                    self.assertTrue(explorer.skills_area.winfo_exists())
                    explorer.hide()
                    self.assertIsNone(explorer._skills_after)
            finally:
                explorer._cancel_search()
                explorer._cancel_skills_layout()
                root.destroy()
