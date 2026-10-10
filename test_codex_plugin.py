import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from unittest.mock import Mock

from quietpet import codex_mcp
from quietpet.integrations import codex


class CodexPluginTests(unittest.TestCase):
    def tearDown(self):
        codex._report = None

    def test_status_expiry(self):
        with patch.object(codex.time, 'monotonic', return_value=100):
            codex.report_status('busy', 'chat-1', 10)
            self.assertEqual(codex.read_status()[0], 'busy')
        with patch.object(codex.time, 'monotonic', return_value=111):
            self.assertEqual(codex.read_status()[0], 'off')
            self.assertTrue(codex.snapshot()['expired'])
        with self.assertRaises(ValueError):
            codex.report_status('invalid', 'chat-1')

    def test_read_scope_and_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'hello.txt').write_text('abcdef', encoding='utf-8')
            reply = {'ok': True, 'result': {'folder': str(root), 'roots': [str(root)]}}
            with patch.object(codex_mcp.mcp, '_gui', return_value=reply):
                self.assertEqual(codex_mcp.call_tool('quietpet_read_file',
                    {'path': str(root / 'hello.txt'), 'max_chars': 3}), 'abc…')
                with self.assertRaises(ValueError):
                    codex_mcp.managed_path(root / '../outside.txt')
                with self.assertRaises(ValueError):
                    codex_mcp.call_tool('quietpet_read_file',
                        {'path': str(root / 'hello.txt'), 'max_chars': -1})

    def test_stdio_handshake_discovery_errors(self):
        requests = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05'}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'bad'}},
        ]
        result = subprocess.run([sys.executable, 'codex_mcp_entry.py'],
            input=''.join(json.dumps(r) + '\n' for r in requests),
            capture_output=True, text=True, encoding='utf-8', timeout=15,
            cwd=Path(__file__).resolve().parent)
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(responses), 3)
        names = {t['name'] for t in responses[1]['result']['tools']}
        self.assertIn('quietpet_codex_status', names)
        self.assertNotIn('quietpet_status', names)
        self.assertTrue(responses[2]['result']['isError'])

    def test_gui_dispatch_and_disconnection(self):
        from quietpet.app import QuietPet
        app = object.__new__(QuietPet)
        app.explorer = Mock()
        app.settings = {}
        app.dock_pet = Mock()
        app._panel_visible = Mock(return_value=True)
        with patch.object(codex_mcp.mcp, '_gui', side_effect=app._control):
            result = json.loads(codex_mcp.call_tool('quietpet_codex_status',
                {'kind': 'busy', 'session_id': 'chat-test'}))
            self.assertTrue(result['ok'])
            self.assertEqual(codex.read_status()[0], 'busy')
            codex_mcp.call_tool('quietpet_panel', {'action': 'show'})
            app.explorer.show.assert_called_once()
            codex_mcp.call_tool('quietpet_side', {'side': 'left'})
            app.explorer.set_side.assert_called_once_with('left')
            app.dock_pet.assert_called_once()
            with tempfile.TemporaryDirectory() as folder:
                codex_mcp.call_tool('quietpet_open_folder', {'path': folder})
                app.explorer.set_folder.assert_called_once_with(Path(folder))
        with patch.object(codex_mcp.mcp, '_gui', return_value={'ok': False, 'error': 'offline'}):
            with self.assertRaisesRegex(RuntimeError, 'offline'):
                codex_mcp.call_tool('quietpet_panel', {'action': 'show'})


if __name__ == '__main__':
    unittest.main()
