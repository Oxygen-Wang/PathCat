"""Project .gitignore/.cursorignore display filters using Git wildmatch syntax."""
from functools import lru_cache
from pathlib import Path
import os
import tempfile
from .._vendor.pathspec import GitIgnoreSpec

IGNORE_FILES = ('.gitignore', '.cursorignore')
DEFAULT_PATTERNS = []


def escape_pattern(path):
    return ''.join('\\' + char if char in '\\*?[]' else char for char in path)


@lru_cache(maxsize=256)
def _compile(lines):
    return GitIgnoreSpec.from_lines(lines)


def _safe_ignore_file(root, filename):
    if filename not in IGNORE_FILES:
        raise ValueError('Only .gitignore and .cursorignore are supported')
    path = Path(root) / filename
    if path.is_symlink():
        raise ValueError('Ignore files must not be symbolic links')
    return path


def read_ignore_lines(root, filename='.cursorignore'):
    path = _safe_ignore_file(root, filename)
    try:
        return path.read_text(encoding='utf-8-sig').splitlines()
    except FileNotFoundError:
        return []


def write_ignore_lines(root, lines, filename='.cursorignore'):
    path = _safe_ignore_file(root, filename)
    _compile(tuple(lines))
    content = '\n'.join(lines) + ('\n' if lines else '')
    if not path.exists() and not content:
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                prefix='.quietpet-ignore-', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def is_ignored(path, root, patterns):
    try:
        relative = Path(path).absolute().relative_to(Path(root).absolute())
    except ValueError:
        return False
    spec = _compile(tuple(patterns))
    for index in range(1, len(relative.parts) + 1):
        candidate = '/'.join(relative.parts[:index])
        if index < len(relative.parts) or (Path(path).is_dir() and not Path(path).is_symlink()):
            candidate += '/'
        if spec.match_file(candidate):
            return True
    return False


@lru_cache(maxsize=256)
def _file_spec(path, modified, size):
    return _compile(tuple(Path(path).read_text(encoding='utf-8-sig').splitlines()))


def _load_spec(directory, filename):
    path = directory / filename
    if path.is_symlink() or not path.is_file():
        return None
    metadata = path.stat()
    return _file_spec(str(path), metadata.st_mtime_ns, metadata.st_size)


def project_ignored(path, root):
    """Union of independent ignore sources, with nested scope and negation.

    A .cursorignore negation cannot re-include a Git-ignored file. These are
    display filters regardless of whether a file is tracked in Git.
    """
    root, path = Path(root).absolute(), Path(path).absolute()
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    if '.git' in relative.parts:
        return True
    for filename in IGNORE_FILES:
        scopes = []
        for index in range(1, len(relative.parts) + 1):
            parent = root.joinpath(*relative.parts[:index - 1])
            spec = _load_spec(parent, filename)
            if spec:
                scopes.append((parent, spec))
            node = root.joinpath(*relative.parts[:index])
            directory = index < len(relative.parts) or (node.is_dir() and not node.is_symlink())
            ignored = False
            for base, spec in scopes:
                candidate = node.relative_to(base).as_posix() + ('/' if directory else '')
                match = spec.check_file(candidate).include
                if match is not None:
                    ignored = match
            if ignored:
                return True
    return False


def transfer_allowed(src, destination):
    source, target = Path(src).resolve(), Path(destination).resolve()
    return not (source == target or source.parent == target or
                (Path(src).is_dir() and source in target.parents))


def top_level_paths(paths):
    unique = list(dict.fromkeys(Path(p) for p in paths))
    return [p for p in unique if not any(q != p and q.is_dir() and
            q.resolve() in p.resolve().parents for q in unique)]
