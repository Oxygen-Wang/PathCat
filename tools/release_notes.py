"""Extract exactly the current version's changelog for a GitHub Release."""
import argparse
import re
from pathlib import Path

from check_version import check

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    version = check()
    changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    section = re.search(r'^## \[' + re.escape(version) + r'\].*?\n(.*?)(?=^## |\Z)',
                        changelog, flags=re.M | re.S)
    if section is None:
        raise SystemExit('No current version changelog found')
    args.out.write_text(f'# PathCat {version}\n\n' + section.group(1).strip() + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
