# -*- coding: utf-8 -*-
"""Shared configuration, paths and palette for QuietPet."""
import json
import os
import sys
from pathlib import Path

IS_WIN = sys.platform == 'win32'
APP = 'PathCat'
VERSION = (Path(__file__).resolve().parents[2] / 'VERSION').read_text(encoding='utf-8').strip()

HOME = Path(os.getenv('USERPROFILE') or Path.home())
# Preserve existing preferences when upgrading from the QuietPet name.
DATA = Path(os.getenv('APPDATA') or HOME) / 'QuietPet'
DATA.mkdir(parents=True, exist_ok=True)
PREFS = DATA / 'settings.json'
DEFAULT_FOLDER = HOME / 'Documents' / APP

# Default summon shortcut. Other combinations or double-tap gestures can be
# selected from the pet's right-click menu.
DEFAULT_HOTKEY = 'Shift+Z'
FONT_SIZE = 10
# Teaching is opened explicitly from the pet menu.
TUTORIAL_TEST_MODE = False


def apply_font_size(value):
    global FONT_SIZE
    try:
        FONT_SIZE = max(8, min(20, int(value)))
    except (TypeError, ValueError):
        FONT_SIZE = 10
    return FONT_SIZE


def ui_font(size=10, weight=None):
    result = ('Segoe UI', max(8, round(size * FONT_SIZE / 10)))
    return result + (weight,) if weight else result

# Palette (Cursor / VS Code dark sidebar feel)
BG = '#1e1f22'
FG = '#d4d6da'
MUTED = '#8a8f98'
BTN = '#2a2c31'
BTN_HOVER = '#3a3d43'
SEL = '#264f78'
SEL_FG = '#ffffff'
DROP_BG = '#385a48'


def apply_theme(name):
    from .themes import palette, PALETTES
    selected = name if name in PALETTES else 'dark'
    globals().update(palette(selected))
    return selected

# Read local skills without changing their documents.
GLOBAL_SKILL_SOURCES = [HOME / '.claude/skills', HOME / '.agents/skills',
                        HOME / '.config/opencode/skills', HOME / '.cursor/skills',
                        HOME / '.codex/skills']
PROJECT_SKILL_SUBDIRS = ['.claude/skills', '.agents/skills', '.opencode/skills',
                        '.cursor/skills', '.codex/skills']
OC_CONFIG = HOME / '.config/opencode/opencode.json'

# Tree helpers
TRASH = '.quietpet_trash'
PLACEHOLDER = '::__qpph__'

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
