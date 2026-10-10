# -*- coding: utf-8 -*-
"""Launcher for QuietPet.

Kept as a top-level script so the .bat file and PyInstaller still work.
The implementation now lives in the ``quietpet`` package.
"""
from quietpet.app import main

if __name__ == '__main__':
    main()
