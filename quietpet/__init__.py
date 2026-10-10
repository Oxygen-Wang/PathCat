# -*- coding: utf-8 -*-
"""QuietPet package: a minimal Windows desktop pet + folder explorer."""
from .core.config import VERSION as __version__
from .app import QuietPet, main

__all__ = ['QuietPet', 'main', '__version__']
