# -*- coding: utf-8 -*-
"""Shared configuration, paths and palette for QuietPet."""
import json
import os
import sys
from pathlib import Path

IS_WIN = sys.platform == 'win32'
APP = 'QuietPet'
VERSION = '0.1.0'

HOME = Path(os.getenv('USERPROFILE') or Path.home())
DATA = Path(os.getenv('APPDATA') or HOME) / APP
DATA.mkdir(parents=True, exist_ok=True)
PREFS = DATA / 'settings.json'
DEFAULT_FOLDER = HOME / 'Documents' / APP

# Default summon gesture: double-tap the Alt key. Can be changed to any key
# combination (e.g. "Ctrl+Alt+Q") or another double-tap (Ctrl/Shift/Win) from
# the pet's right-click menu.
DEFAULT_HOTKEY = 'Alt'

# opencode related locations
GLOBAL_SKILL_SOURCES = [
    HOME / '.claude' / 'skills',
    HOME / '.agents' / 'skills',
    HOME / '.config' / 'opencode' / 'skills',
]
PROJECT_SKILL_SUBDIRS = ['.claude/skills', '.agents/skills', '.opencode/skills']
OC_CONFIG = HOME / '.config' / 'opencode' / 'opencode.json'
OC_DB_CANDIDATES = [
    HOME / '.local' / 'share' / 'opencode' / 'opencode.db',
    Path(os.getenv('LOCALAPPDATA') or HOME) / 'opencode' / 'opencode.db',
]

# Local control channel used by the MCP bridge (localhost only).
CONTROL_PORT = 8765

# Palette (Cursor / VS Code dark sidebar feel)
BG = '#1e1f22'
FG = '#d4d6da'
MUTED = '#8a8f98'
BTN = '#2a2c31'
BTN_HOVER = '#3a3d43'
SEL = '#264f78'

# Tree helpers
TRASH = '.quietpet_trash'
PLACEHOLDER = '::__qpph__'
SEC_SKILLS = '__sec_skills__'
SEC_MCP = '__sec_mcp__'
SKILL_PREFIX = '__skill__::'
MCP_PREFIX = '__mcp__::'

STATUS_STYLES = {
    'busy': ('#f0a020', '工作中'),
    'idle': ('#5aa469', '空闲'),
    'wait': ('#e06c75', '等待中'),
    'off': ('#6b7079', '离线'),
}

FILE_ICONS = {
    '.py': '🐍', '.js': '🟨', '.ts': '🟦', '.json': '🔸', '.md': '📘',
    '.txt': '📄', '.log': '📄', '.ini': '⚙', '.cfg': '⚙', '.toml': '⚙',
    '.png': '🖼', '.jpg': '🖼', '.jpeg': '🖼', '.gif': '🖼', '.bmp': '🖼',
    '.svg': '🖼', '.ico': '🖼', '.pdf': '📕', '.doc': '📘', '.docx': '📘',
    '.ppt': '📙', '.pptx': '📙', '.xls': '📗', '.xlsx': '📗',
    '.zip': '🗜', '.rar': '🗜', '.7z': '🗜', '.exe': '⚙', '.bat': '⚙',
    '.cmd': '⚙', '.lnk': '🔗', '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵',
    '.mp4': '🎬', '.mkv': '🎬', '.avi': '🎬', '.html': '🌐', '.htm': '🌐',
    '.css': '🎨', '.db': '🗄', '.sql': '🗄', '.ttf': '🔤',
}


def load_settings():
    for encoding in ('utf-8-sig', 'utf-8'):
        try:
            return json.loads(PREFS.read_text(encoding=encoding))
        except Exception:
            continue
    return {}


def save_settings(settings):
    PREFS.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding='utf-8')
