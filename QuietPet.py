# -*- coding: utf-8 -*-
"""QuietPet launcher.

Runs the GUI by default, or the MCP stdio server with ``--mcp``:

    python QuietPet.py
    python QuietPet.py --mcp
"""
import sys


def main():
    if '--mcp' in sys.argv:
        from quietpet.mcp import main as mcp_main
        mcp_main()
    else:
        from quietpet.app import main as app_main
        app_main()


if __name__ == '__main__':
    main()
