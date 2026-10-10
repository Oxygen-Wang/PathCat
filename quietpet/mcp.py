# -*- coding: utf-8 -*-
"""Minimal MCP server (stdio, newline-delimited JSON-RPC).

Exposes QuietPet as tools an MCP client (opencode) can call: status, skills,
directory listing, and GUI actions (open folder, show/hide panel, docking side).

Run with:  python QuietPet.py --mcp
Register:  opencode mcp add quietpet -- python QuietPet.py --mcp
"""
import json
import sys
from pathlib import Path

from . import control
from .core import config
from .core.config import VERSION as __version__
from .opencode import status

SERVER_INFO = {'name': 'quietpet', 'version': __version__}
PROTOCOL = '2024-11-05'

TOOLS = [
    {
        'name': 'quietpet_status',
        'description': 'Get the current opencode status shown on the pet (working/idle/waiting/offline).',
        'inputSchema': {'type': 'object', 'properties': {}},
    },
    {
        'name': 'quietpet_skills',
        'description': 'List opencode agent skills discovered on this machine (id, name, description, path).',
        'inputSchema': {
            'type': 'object',
            'properties': {'project_dir': {'type': 'string', 'description': 'Optional project folder to include project skills.'}},
        },
    },
    {
        'name': 'quietpet_mcp_servers',
        'description': 'List the MCP servers configured for opencode (name, type, url/command, disabled).',
        'inputSchema': {'type': 'object', 'properties': {}},
    },
    {
        'name': 'quietpet_list_dir',
        'description': 'List the entries of a folder (defaults to the pet\'s current folder).',
        'inputSchema': {
            'type': 'object',
            'properties': {'path': {'type': 'string', 'description': 'Folder to list.'}},
        },
    },
    {
        'name': 'quietpet_read_file',
        'description': 'Read a small text file (truncated).',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'path': {'type': 'string'},
                'max_chars': {'type': 'integer'},
            },
            'required': ['path'],
        },
    },
    {
        'name': 'quietpet_info',
        'description': 'Get the pet GUI state: current folder, roots, dock side, width, version.',
        'inputSchema': {'type': 'object', 'properties': {}},
    },
    {
        'name': 'quietpet_open_folder',
        'description': 'Open/switch the folder shown in the QuietPet sidebar.',
        'inputSchema': {
            'type': 'object',
            'properties': {'path': {'type': 'string'}},
            'required': ['path'],
        },
    },
    {
        'name': 'quietpet_panel',
        'description': 'Show, hide or toggle the QuietPet sidebar panel.',
        'inputSchema': {
            'type': 'object',
            'properties': {'action': {'type': 'string', 'enum': ['show', 'hide', 'toggle']}},
            'required': ['action'],
        },
    },
    {
        'name': 'quietpet_side',
        'description': 'Dock the sidebar to the left or right, and move the cat accordingly.',
        'inputSchema': {
            'type': 'object',
            'properties': {'side': {'type': 'string', 'enum': ['left', 'right']}},
            'required': ['side'],
        },
    },
]


def _gui(cmd, args=None):
    try:
        return control.send_command(cmd, args)
    except Exception as exc:
        return {'ok': False, 'error': 'QuietPet GUI not running (%s)' % exc}


def _dir(path):
    p = Path(path)
    out = []
    for entry in sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.casefold())):
        try:
            out.append({'name': entry.name, 'dir': entry.is_dir(),
                        'size': entry.stat().st_size if entry.is_file() else None})
        except OSError:
            out.append({'name': entry.name, 'dir': entry.is_dir(), 'size': None})
    return out


def call_tool(name, args):
    if name == 'quietpet_status':
        kind, label = status.read_opencode_status() or ('off', '离线')
        return json.dumps({'kind': kind, 'label': label}, ensure_ascii=False)
    if name == 'quietpet_skills':
        skills = status.list_open_skills(project_dir=args.get('project_dir'),
                                         config_paths=[config.OC_CONFIG])
        return json.dumps(
            [{'id': s['id'], 'name': s['name'], 'description': s['description'],
              'path': str(s['path'])} for s in skills], ensure_ascii=False, indent=2)
    if name == 'quietpet_mcp_servers':
        servers = status.read_mcp_servers([config.OC_CONFIG])
        return json.dumps(servers, ensure_ascii=False, indent=2)
    if name == 'quietpet_read_file':
        p = Path(args['path'])
        text = p.read_text(encoding='utf-8', errors='ignore')
        limit = int(args.get('max_chars') or 6000)
        return text[:limit] + ('…' if len(text) > limit else '')
    if name == 'quietpet_list_dir':
        path = args.get('path')
        if not path:
            reply = _gui('info')
            path = (reply.get('result') or {}).get('folder') if reply.get('ok') else None
            path = path or str(config.DEFAULT_FOLDER)
        return json.dumps(_dir(path), ensure_ascii=False, indent=2)
    if name == 'quietpet_info':
        return json.dumps(_gui('info'), ensure_ascii=False)
    if name == 'quietpet_open_folder':
        return json.dumps(_gui('open_folder', {'path': args.get('path')}), ensure_ascii=False)
    if name == 'quietpet_panel':
        return json.dumps(_gui('panel', {'action': args.get('action', 'toggle')}), ensure_ascii=False)
    if name == 'quietpet_side':
        return json.dumps(_gui('side', {'side': args.get('side', 'right')}), ensure_ascii=False)
    raise ValueError('unknown tool: %s' % name)


def _respond(rid, result=None, error=None):
    msg = {'jsonrpc': '2.0', 'id': rid}
    if error is not None:
        msg['error'] = error
    else:
        msg['result'] = result
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + '\n')
    sys.stdout.flush()


def main(resource_list=None, resource_handler=None, tool_handler=None):
    try:
        sys.stdout.reconfigure(encoding='utf-8', newline='\n')
        sys.stdin.reconfigure(encoding='utf-8')
    except Exception:
        pass
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        method = msg.get('method')
        rid = msg.get('id')
        if method == 'initialize':
            params = msg.get('params') or {}
            _respond(rid, {'protocolVersion': params.get('protocolVersion', PROTOCOL),
                           'capabilities': dict({'tools': {}}, **({'resources': {}} if resource_list else {})),
                           'serverInfo': SERVER_INFO})
        elif method in ('notifications/initialized', 'initialized'):
            pass
        elif method == 'ping':
            _respond(rid, {})
        elif method == 'tools/list':
            _respond(rid, {'tools': TOOLS})
        elif method == 'resources/list' and resource_list is not None:
            _respond(rid, {'resources': resource_list})
        elif method == 'resources/read' and resource_handler is not None:
            try:
                _respond(rid, resource_handler((msg.get('params') or {}).get('uri')))
            except Exception as exc:
                _respond(rid, error={'code': -32602, 'message': str(exc)})
        elif method == 'tools/call':
            params = msg.get('params') or {}
            try:
                output = (tool_handler or call_tool)(params.get('name'), params.get('arguments') or {})
                _respond(rid, output if isinstance(output, dict) else
                         {'content': [{'type': 'text', 'text': output}], 'isError': False})
            except Exception as exc:
                _respond(rid, {'content': [{'type': 'text', 'text': 'error: %s' % exc}], 'isError': True})
        elif rid is not None:
            _respond(rid, error={'code': -32601, 'message': 'method not found: %s' % method})


if __name__ == '__main__':
    main()
