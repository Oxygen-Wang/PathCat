"""Codex-specific MCP tools with reads limited to GUI-managed folders."""
import json
from pathlib import Path

from . import mcp
from .opencode.status import _iter_skills_in, _frontmatter
from .core.config import HOME


def tool(name, description, properties=None, required=None):
    return {'name': name, 'description': description,
            'inputSchema': {'type': 'object', 'properties': properties or {},
                            'required': required or [], 'additionalProperties': False}}


TEXT = {'type': 'string'}
WIDGET_URI = 'ui://quietpet/file-panel.html'
WIDGET_PATH = Path(__file__).resolve().parents[1] / 'plugins/quietpet-codex/ui/file-panel.html'
TOOLS = [t for t in mcp.TOOLS if t['name'] in {
    'quietpet_info', 'quietpet_open_folder', 'quietpet_panel', 'quietpet_side',
    'quietpet_list_dir', 'quietpet_read_file'}] + [
    tool('quietpet_codex_status', 'Report this Codex task status to the desktop pet. Last report wins; refresh long tasks before TTL expires.',
         {'kind': {'type': 'string', 'enum': ['busy', 'idle', 'wait', 'off']},
          'session_id': TEXT, 'ttl': {'type': 'integer', 'minimum': 10, 'maximum': 3600}},
         ['kind', 'session_id']),
    tool('quietpet_codex_skills', 'List local Codex skill metadata, not skill execution. Project must be a GUI-managed folder.',
         {'project_dir': TEXT}),
]
TOOLS += [
    tool('quietpet_theme', 'Change QuietPet interface colors; does not modify Windows colors.',
         {'name': {'type': 'string', 'enum': ['dark', 'light', 'cream', 'sage', 'slate']}}, ['name']),
    tool('quietpet_file_panel', 'Open the interactive project file panel where the host supports MCP Apps. Returns file data on other hosts.',
         {'path': TEXT, 'show_ignored': {'type': 'boolean'}}),
    tool('quietpet_file_ignore', 'Write the active project .cursorignore or .gitignore. gitignore changes also affect Git; no files are deleted.',
         {'root': TEXT, 'patterns': {'type': 'array', 'items': TEXT}, 'path': TEXT,
          'ignore_file': {'type': 'string', 'enum': ['.gitignore', '.cursorignore']},
          'show_ignored': {'type': 'boolean'}}, ['root', 'patterns']),
    tool('quietpet_file_transfer', 'Move or copy a file/folder within the active project. Refuses recursive transfers; existing names get a unique suffix.',
         {'source': TEXT, 'destination': TEXT, 'mode': {'type': 'string', 'enum': ['move', 'copy']},
          'path': TEXT, 'show_ignored': {'type': 'boolean'}}, ['source', 'destination', 'mode']),
]
TOOLS[-3]['_meta'] = {'ui': {'resourceUri': WIDGET_URI},
                      'openai/ui': {'entrypoints': [{'type': 'thread'}]}}
for descriptor in TOOLS[-3:]:
    descriptor['annotations'] = {'readOnlyHint': descriptor['name'] == 'quietpet_file_panel',
                                 'destructiveHint': descriptor['name'] == 'quietpet_file_transfer',
                                 'openWorldHint': False}
_original_call = mcp.call_tool


def managed_path(value=None):
    reply = mcp._gui('info')
    if not reply.get('ok'):
        raise RuntimeError(reply.get('error', 'Start QuietPet first'))
    info = reply['result']
    p = Path(value or info['folder']).resolve()
    roots = [Path(r).resolve() for r in info.get('roots', [])] + [Path(info['folder']).resolve()]
    if not any(p == r or r in p.parents for r in roots):
        raise ValueError('Path is outside QuietPet managed folders. Open the intended project first.')
    return p


def call_tool(name, args):
    if name not in {t['name'] for t in TOOLS}:
        raise ValueError('unknown tool: %s' % name)
    if name == 'quietpet_theme':
        reply = mcp._gui('theme', args)
        if not reply.get('ok'):
            raise RuntimeError(reply.get('error', 'Theme change failed'))
        return json.dumps(reply, ensure_ascii=False)
    commands = {'quietpet_file_panel': 'file_view', 'quietpet_file_ignore': 'file_ignore',
                'quietpet_file_transfer': 'file_transfer'}
    if name in commands:
        reply = mcp._gui(commands[name], args)
        if not reply.get('ok'):
            raise RuntimeError(reply.get('error', 'QuietPet command failed'))
        return {'content': [{'type': 'text', 'text': json.dumps(reply['result'], ensure_ascii=False)}],
                'structuredContent': reply['result'], 'isError': False}
    if name == 'quietpet_codex_status':
        from .integrations.codex import LABELS
        if args.get('kind') not in LABELS or not args.get('session_id'):
            raise ValueError('kind and session_id are required')
        reply = mcp._gui('codex_status', args)
        if not reply.get('ok'):
            raise RuntimeError(reply.get('error', 'QuietPet command failed'))
        return json.dumps(reply, ensure_ascii=False)
    if name == 'quietpet_codex_skills':
        project = managed_path(args.get('project_dir'))
        sources = [HOME / '.codex/skills', HOME / '.agents/skills',
                   project / '.codex/skills', project / '.agents/skills']
        found = {}
        for source in sources:
            for key, path in _iter_skills_in(source):
                title, description = _frontmatter(path)
                found[key] = {'id': key, 'name': title or key, 'description': description, 'path': str(path)}
        return json.dumps(list(found.values()), ensure_ascii=False)
    if name in ('quietpet_read_file', 'quietpet_list_dir'):
        args = dict(args, path=str(managed_path(args.get('path'))))
        if name == 'quietpet_read_file':
            limit = int(args.get('max_chars', 6000))
            if not 1 <= limit <= 100000:
                raise ValueError('max_chars must be between 1 and 100000')
            with Path(args['path']).open(encoding='utf-8', errors='replace') as stream:
                content = stream.read(limit + 1)
            return content[:limit] + ('…' if len(content) > limit else '')
    result = _original_call(name, args)
    if name in ('quietpet_info', 'quietpet_open_folder', 'quietpet_panel', 'quietpet_side'):
        reply = json.loads(result)
        if not reply.get('ok'):
            raise RuntimeError(reply.get('error', 'QuietPet command failed'))
    return result


def main():
    mcp.TOOLS = TOOLS
    mcp.main(resource_list=[{'uri': WIDGET_URI, 'name': 'QuietPet Files',
                            'mimeType': 'text/html;profile=mcp-app'}],
             resource_handler=read_resource, tool_handler=call_tool)


def read_resource(uri):
    if uri != WIDGET_URI:
        raise ValueError('Unknown UI resource')
    return {'contents': [{'uri': uri, 'mimeType': 'text/html;profile=mcp-app',
                          'text': WIDGET_PATH.read_text(encoding='utf-8'),
                          '_meta': {'ui': {'csp': {'connectDomains': [], 'resourceDomains': []}}}}]}


if __name__ == '__main__':
    main()
