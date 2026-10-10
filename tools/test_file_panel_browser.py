"""Exercise the real widget against real file operations in a simulated MCP Apps host.

This validates the widget, not Codex host rendering support.
Requires playwright and its Chromium browser.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from playwright.sync_api import sync_playwright

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from quietpet import codex_mcp
from quietpet.integrations.file_panel import handle
from quietpet.ui.explorer import Explorer


def main():
    (ROOT / '.test-tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / '.test-tmp') as tmp:
        folder = Path(tmp)
        (folder / 'docs').mkdir()
        (folder / 'node_modules').mkdir()
        (folder / '.gitignore').write_text('node_modules/\n', encoding='utf-8')
        (folder / 'readme.txt').write_text('QuietPet widget preview', encoding='utf-8')
        ex = object.__new__(Explorer)
        ex.folder = folder
        ex.settings = {}
        ex.save = Mock()
        ex.rebuild = Mock()
        ex.on_event = Mock()

        def gui(command, args=None):
            if command == 'theme':
                from quietpet.core import config
                ex.settings['theme'] = config.apply_theme(args['name'])
                return {'ok': True, 'result': {'theme': ex.settings['theme']}}
            if command == 'info':
                return {'ok': True, 'result': {'folder': str(folder), 'roots': [str(folder)]}}
            return {'ok': True, 'result': handle(ex, command, args or {})}

        def host_tool(name, args):
            try:
                with patch.object(codex_mcp.mcp, '_gui', side_effect=gui):
                    response = codex_mcp.call_tool(name, args)
                    if isinstance(response, str):
                        return {'content': [{'type': 'text', 'text': response}], 'isError': False}
                    return response
            except Exception as error:
                return {'content': [{'type': 'text', 'text': str(error)}], 'isError': True}

        html = codex_mcp.WIDGET_PATH.read_text(encoding='utf-8')
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 880, 'height': 720})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.expose_function('hostTool', host_tool)
            page.set_content('''<iframe id="widget" style="width:100%;height:680px;border:0"></iframe>
                <script>
                window.addEventListener('message', async event => {
                  const msg = event.data;
                  if (event.source !== document.querySelector('iframe').contentWindow || !msg.id) return;
                  let result;
                  if (msg.method === 'ui/initialize') result = {protocolVersion:'2026-01-26',hostInfo:{name:'test-host',version:'1'},hostCapabilities:{}};
                  else if (msg.method === 'tools/call') result = await window.hostTool(msg.params.name,msg.params.arguments);
                  else return;
                  event.source.postMessage({jsonrpc:'2.0',id:msg.id,result}, '*');
                });
                </script>''')
            page.eval_on_selector('#widget', '(frame, html) => frame.srcdoc = html', html)
            widget = page.frame_locator('#widget')
            widget.get_by_role('button', name='readme.txt', exact=True).wait_for()
            for theme in ('light', 'cream', 'sage', 'slate', 'dark'):
                widget.get_by_label('界面配色').select_option(theme)
                widget.locator('#status').get_by_text('已更新', exact=True).wait_for()
                assert ex.settings['theme'] == theme
                from quietpet.core.themes import palette
                assert widget.locator('html').evaluate("el => el.style.getPropertyValue('--bg')") == palette(theme)['BG']
            assert widget.get_by_role('button', name='node_modules', exact=True).count() == 0
            widget.get_by_role('button', name='readme.txt', exact=True).click()
            widget.locator('#preview-text').get_by_text('QuietPet widget preview').wait_for()
            # The real drag listeners call the real backend through the host bridge.
            widget.locator('.row').filter(has=widget.get_by_role('button', name='readme.txt', exact=True)).drag_to(
                widget.locator('.row').filter(has=widget.get_by_role('button', name='docs', exact=True)))
            widget.get_by_role('button', name='readme.txt', exact=True).wait_for(state='detached')
            assert (folder / 'docs/readme.txt').exists()
            assert not (folder / 'readme.txt').exists()
            widget.get_by_role('button', name='docs', exact=True).click()
            widget.get_by_role('button', name='readme.txt', exact=True).wait_for()
            widget.locator('.row').filter(has=widget.get_by_role('button', name='readme.txt', exact=True)).get_by_role('button', name='忽略', exact=True).click()
            widget.get_by_role('button', name='readme.txt', exact=True).wait_for(state='detached')
            assert (folder / 'docs/readme.txt').exists()
            widget.get_by_label('显示忽略项').check()
            widget.get_by_role('button', name='readme.txt', exact=True).wait_for()
            widget.get_by_role('button', name='忽略规则', exact=True).click()
            widget.get_by_label('忽略规则', exact=True).fill('')
            widget.get_by_role('button', name='保存规则', exact=True).click()
            widget.locator('#editor').wait_for(state='hidden')
            assert ex.ignore_patterns() == []
            assert (folder / '.gitignore').read_text() == 'node_modules/\n'
            # Holding Ctrl copies to the parent through the up-button drop zone.
            page.keyboard.down('Control')
            widget.locator('.row').filter(has=widget.get_by_role('button', name='readme.txt', exact=True)).drag_to(
                widget.get_by_role('button', name='上一级', exact=True))
            page.keyboard.up('Control')
            widget.locator('#status').get_by_text('已更新', exact=True).wait_for()
            assert (folder / 'readme.txt').exists()
            assert (folder / 'docs/readme.txt').exists()
            widget.get_by_role('button', name='上一级', exact=True).click()
            widget.get_by_role('button', name='docs', exact=True).wait_for()
            page.screenshot(path=str(ROOT / 'dist/QuietPetFilePanel-test.png'))
            assert not errors, errors
            browser.close()
            print(json.dumps({'host': 'simulated MCP Apps host', 'checks': [
                'bridge initialization', 'five persistent themes', 'real directory listing', 'text preview',
                'drag move with real files', 'Ctrl drag copy with real files', 'ignore without delete',
                'show ignored', 'edit and restore rules', 'parent navigation'],
                'javascript_errors': errors}, ensure_ascii=False))


if __name__ == '__main__':
    main()
