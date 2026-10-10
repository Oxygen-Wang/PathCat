# -*- coding: utf-8 -*-
"""Compatibility launcher for the PathCat desktop application."""
import argparse


def main():
    parser = argparse.ArgumentParser(description='PathCat desktop file sidebar')
    parser.add_argument('--version', action='store_true', help='Print the desktop version')
    args = parser.parse_args()
    if args.version:
        from quietpet.core.config import APP, VERSION
        print(f'{APP} {VERSION}')
        return
    from quietpet.app import main as app_main
    app_main()


if __name__ == '__main__':
    main()
