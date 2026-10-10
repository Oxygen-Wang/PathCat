import tempfile
import unittest
from pathlib import Path

from quietpet.core.ignore import project_ignored, write_ignore_lines


class ProjectIgnoreTests(unittest.TestCase):
    def test_git_cursor_union_negation_and_nested_scopes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'src/deep').mkdir(parents=True)
            (root / '.gitignore').write_text('*.log\n!keep.log\n**/cache/\n', encoding='utf-8')
            (root / '.cursorignore').write_text('*.secret\n!public.secret\n!debug.log\n', encoding='utf-8')
            for name in ('debug.log', 'keep.log', 'key.secret', 'public.secret'):
                (root / name).write_text('data')
            self.assertTrue(project_ignored(root / 'debug.log', root))
            self.assertFalse(project_ignored(root / 'keep.log', root))
            self.assertTrue(project_ignored(root / 'key.secret', root))
            self.assertFalse(project_ignored(root / 'public.secret', root))
            (root / 'src/cache').mkdir()
            self.assertTrue(project_ignored(root / 'src/cache', root))
            (root / 'src/.gitignore').write_text('!debug.log\n', encoding='utf-8')
            (root / 'src/debug.log').write_text('visible')
            self.assertFalse(project_ignored(root / 'src/debug.log', root))
            self.assertTrue(project_ignored(root / 'other/debug.log', root))

    def test_directory_exclusion_and_live_file_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'hidden').mkdir()
            (root / 'hidden/keep.txt').write_text('data')
            ignore = root / '.gitignore'
            ignore.write_text('hidden/\n!hidden/keep.txt\n')
            self.assertTrue(project_ignored(root / 'hidden/keep.txt', root))
            ignore.write_text('hidden/*\n!hidden/keep.txt\n')
            self.assertFalse(project_ignored(root / 'hidden/keep.txt', root))
            write_ignore_lines(root, ['# preserve comments', '', '*.tmp', '!keep.tmp'])
            self.assertEqual((root / '.cursorignore').read_text(), '# preserve comments\n\n*.tmp\n!keep.tmp\n')
            self.assertTrue(project_ignored(root / 'run.tmp', root))
            self.assertFalse(project_ignored(root / 'keep.tmp', root))
            with self.assertRaises(ValueError):
                write_ignore_lines(root, ['*'], '../outside')


if __name__ == '__main__':
    unittest.main()
