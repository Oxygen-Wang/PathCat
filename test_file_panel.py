import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from quietpet.ui.explorer import Explorer
from quietpet.integrations.file_panel import handle
from quietpet.codex_mcp import WIDGET_URI


class FilePanelTests(unittest.TestCase):
    def test_real_files_and_display_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'target').mkdir()
            (root / 'node_modules').mkdir()
            (root / '.gitignore').write_text('node_modules/\n')
            (root / 'readme.txt').write_text('original')
            ex = object.__new__(Explorer)
            ex.folder = root
            ex.settings = {}
            ex.save = Mock()
            ex.rebuild = Mock()
            ex.on_event = Mock()
            result = handle(ex, 'file_view', {})
            self.assertNotIn('node_modules', [e['name'] for e in result['entries']])
            self.assertIn('readme.txt', [e['name'] for e in result['entries']])
            handle(ex, 'file_ignore', {'root': str(root), 'patterns': ['*.txt']})
            self.assertNotIn('readme.txt', [e['name'] for e in handle(ex, 'file_view', {})['entries']])
            self.assertTrue((root / 'readme.txt').exists())
            handle(ex, 'file_transfer', {'source': str(root / 'readme.txt'),
                   'destination': str(root / 'target'), 'mode': 'copy'})
            self.assertTrue((root / 'readme.txt').exists())
            self.assertEqual((root / 'target/readme.txt').read_text(), 'original')
            handle(ex, 'file_transfer', {'source': str(root / 'readme.txt'),
                   'destination': str(root / 'target'), 'mode': 'move'})
            self.assertFalse((root / 'readme.txt').exists())
            self.assertEqual(len(list((root / 'target').iterdir())), 2)
            with self.assertRaises(ValueError):
                handle(ex, 'file_transfer', {'source': str(root / 'target'),
                       'destination': str(root / 'target'), 'mode': 'move'})
            with self.assertRaises(ValueError):
                handle(ex, 'file_ignore', {'root': str(root.parent), 'patterns': []})
            with self.assertRaises(ValueError):
                handle(ex, 'file_view', {'path': str(root.parent)})

    def test_ui_resource_protocol(self):
        messages = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'resources/list'},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'resources/read', 'params': {'uri': WIDGET_URI}},
            {'jsonrpc': '2.0', 'id': 4, 'method': 'resources/read', 'params': {'uri': 'file:///secret'}},
        ]
        completed = subprocess.run([sys.executable, 'codex_mcp_entry.py'],
            input=''.join(json.dumps(m) + '\n' for m in messages), capture_output=True,
            text=True, encoding='utf-8', timeout=15, cwd=Path(__file__).resolve().parent)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        responses = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertIn('resources', responses[0]['result']['capabilities'])
        self.assertEqual(responses[1]['result']['resources'][0]['uri'], WIDGET_URI)
        html = responses[2]['result']['contents'][0]
        self.assertEqual(html['mimeType'], 'text/html;profile=mcp-app')
        self.assertIn('ui/initialize', html['text'])
        self.assertIn('quietpet_file_transfer', html['text'])
        self.assertIn('error', responses[3])


if __name__ == '__main__':
    unittest.main()
