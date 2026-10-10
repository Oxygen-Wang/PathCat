"""File panel operations dispatched on the GUI thread."""
from pathlib import Path

from ..core.ignore import project_ignored, transfer_allowed, IGNORE_FILES
from ..core import config
from ..core.themes import palette


def scoped_path(explorer, value=None):
    root = explorer.folder.resolve()
    path = Path(value or root).resolve()
    if path != root and root not in path.parents:
        raise ValueError('Path is outside the active project')
    return path


def view(explorer, args):
    root = explorer.folder.resolve()
    path = scoped_path(explorer, args.get('path'))
    if not path.is_dir():
        raise ValueError('Not a folder')
    patterns = list(explorer.ignore_patterns())
    entries = []
    for item in path.iterdir():
        if item.name == '.quietpet_trash':
            continue
        ignored = project_ignored(item, root)
        if ignored and not args.get('show_ignored', False):
            continue
        entries.append({'name': item.name, 'path': str(item), 'dir': item.is_dir(),
                        'ignored': ignored, 'link': item.is_symlink()})
    entries.sort(key=lambda entry: (not entry['dir'], entry['name'].casefold()))
    return {'root': str(root), 'path': str(path), 'parent': str(path.parent) if path != root else None,
            'entries': entries, 'patterns': patterns,
            'ignore_files': {name: explorer.ignore_patterns(name) for name in IGNORE_FILES},
            'show_ignored': bool(args.get('show_ignored')),
            'theme': explorer.settings.get('theme', 'dark'),
            'palette': palette(explorer.settings.get('theme', 'dark'))}


def handle(explorer, command, args):
    if command == 'file_view':
        return view(explorer, args)
    if command == 'file_ignore':
        if not args.get('root'):
            raise ValueError('root is required')
        view(explorer, args)  # Validate the requested view before changing settings.
        # Bind saved settings to the project shown when the edit began.
        if scoped_path(explorer, args.get('root')) != explorer.folder.resolve():
            raise ValueError('Active project changed; refresh the panel')
        patterns = args.get('patterns')
        if not isinstance(patterns, list) or len(patterns) > 500 or any(
                not isinstance(rule, str) or len(rule) > 500 for rule in patterns):
            raise ValueError('Invalid ignore patterns')
        explorer.set_ignore_patterns(patterns, args.get('ignore_file', '.cursorignore'))
        return view(explorer, args)
    if command == 'file_transfer':
        if not args.get('source') or not args.get('destination'):
            raise ValueError('source and destination are required')
        view(explorer, args)
        if Path(args['source']).is_symlink():
            raise ValueError('Symbolic-link sources are not supported')
        source = scoped_path(explorer, args.get('source'))
        target = scoped_path(explorer, args.get('destination'))
        if not source.exists() or not target.is_dir():
            raise ValueError('Source or destination no longer exists')
        if not transfer_allowed(source, target):
            raise ValueError('Cannot drop here: same location or inside the source folder')
        mode = args.get('mode')
        if mode not in ('copy', 'move'):
            raise ValueError('Invalid transfer mode')
        if mode == 'copy':
            explorer._copy_path(source, target)
        else:
            explorer._move_path(source, target)
        explorer.rebuild(preserve=True)
        explorer.on_event('file_copy' if mode == 'copy' else 'file_move')
        return view(explorer, args)
    raise ValueError('Unknown file panel command')
