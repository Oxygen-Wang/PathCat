# -*- coding: utf-8 -*-
"""Allow running with:  python -m quietpet   (GUI)  or  python -m quietpet --mcp"""
import sys


def main():
    if '--mcp' in sys.argv:
        from .mcp import main as mcp_main
        mcp_main()
    else:
        from .app import main as app_main
        app_main()


if __name__ == '__main__':
    main()
