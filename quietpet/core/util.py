# -*- coding: utf-8 -*-
"""Small pure helpers: name validation, unique names, jsonc parsing."""
import re
from pathlib import Path


def safe_name(value):
    value = (value or '').strip()
    if not value or value in ('.', '..') or any(c in value for c in '<>:"/\\|?*') or value.endswith((' ', '.')):
        raise ValueError('名称无效或包含 Windows 不允许的字符')
    return value


def unique_dest(parent, name):
    dest = Path(parent) / name
    if not dest.exists():
        return dest
    p = Path(name)
    stem, suffix = p.stem, p.suffix
    for i in range(2, 10000):
        result = Path(parent) / f'{stem} ({i}){suffix}'
        if not result.exists():
            return result
    raise RuntimeError('无法生成不重复的名称')


def strip_jsonc(text):
    """Best-effort conversion of jsonc text into plain JSON."""
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'(?m)(?<!:)//.*?$', '', text)
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    return text
