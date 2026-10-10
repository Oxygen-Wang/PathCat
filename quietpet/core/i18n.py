# -*- coding: utf-8 -*-
"""Localization: put UI text in a separate folder (quietpet/locale)."""
from .locale import en, zh

LANGUAGES = {'zh': zh, 'en': en}
DEFAULT_LANGUAGE = 'zh'

_current = DEFAULT_LANGUAGE


def available():
    return list(LANGUAGES.keys())


def set_language(lang):
    global _current
    _current = lang if lang in LANGUAGES else DEFAULT_LANGUAGE
    return _current


def get_language():
    return _current


def t(key, **kwargs):
    table = LANGUAGES.get(_current, zh).STRINGS
    text = table.get(key)
    if text is None:
        text = zh.STRINGS.get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
