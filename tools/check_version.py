"""Fail CI when the source, changelog, README or release tag disagree."""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(alpha|beta|rc)\.([1-9]\d*))?'


def check(tag=None):
    version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    if not re.fullmatch(SEMVER, version):
        raise ValueError('VERSION must be SemVer, optionally with -alpha.N, -beta.N or -rc.N')
    if tag is not None and tag != 'v' + version:
        raise ValueError(f'Tag {tag!r} does not match VERSION {version!r}')
    changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    if len(re.findall(r'^## \[' + re.escape(version) + r'\]', changelog, flags=re.M)) != 1:
        raise ValueError('CHANGELOG must contain exactly one section for this version')
    if f'**{version}**' not in (ROOT / 'README.md').read_text(encoding='utf-8'):
        raise ValueError('README current version does not match VERSION')
    result = subprocess.run([sys.executable, str(ROOT / 'PathCat.py'), '--version'],
                            capture_output=True, text=True, check=True)
    if result.stdout.strip() != f'PathCat {version}':
        raise ValueError('Application runtime version does not match VERSION')
    return version


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag')
    args = parser.parse_args()
    print(f'Version checks passed: {check(args.tag)}')


if __name__ == '__main__':
    main()
