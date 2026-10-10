"""Cancellable filename search; no UI calls on the worker thread."""
import os
from pathlib import Path

from . import config
from .ignore import project_ignored


def find_paths(root, query, cancelled, show_ignored=False):
    root = Path(root)
    query = query.strip().casefold()
    if not query:
        return
    for directory, dirs, files in os.walk(root, followlinks=False):
        if cancelled.is_set():
            return
        visible = []
        for name in dirs + files:
            if cancelled.is_set():
                return
            path = Path(directory) / name
            if name == config.TRASH or (not show_ignored and project_ignored(path, root)):
                continue
            visible.append(name)
            if query in name.casefold():
                yield path
        dirs[:] = [name for name in dirs if name in visible and not (Path(directory) / name).is_symlink()]
