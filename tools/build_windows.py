"""Build the desktop EXE and a versioned ZIP with bundled-license sources."""
import hashlib
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

from check_version import check

ROOT = Path(__file__).resolve().parents[1]


def main():
    # Read the interpreter PE machine field; Windows sandbox environments may
    # omit PROCESSOR_ARCHITECTURE, which makes platform.machine() empty.
    interpreter = Path(sys.executable).read_bytes()
    pe_offset = struct.unpack_from('<I', interpreter, 0x3c)[0] if sys.platform == 'win32' else 0
    if sys.platform != 'win32' or struct.unpack_from('<H', interpreter, pe_offset + 4)[0] != 0x8664:
        raise SystemExit('Build on Windows x64 for this release target')
    version = check()
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    build = ROOT / 'build'
    build.mkdir(exist_ok=True)
    numbers = tuple(int(n) for n in version.split('-')[0].split('.'))
    numbers += (int(version.rsplit('.', 1)[1]) if '-' in version else 0,)
    resource = build / 'PathCat-version.txt'
    resource.write_text(
        f"VSVersionInfo(ffi=FixedFileInfo(filevers={numbers!r}, prodvers={numbers!r}, "
        "mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)), "
        "kids=[StringFileInfo([StringTable('040904B0', ["
        "StringStruct('ProductName', 'PathCat'), StringStruct('FileDescription', 'PathCat desktop file sidebar'), "
        f"StringStruct('FileVersion', {version!r}), StringStruct('ProductVersion', {version!r}), "
        "StringStruct('OriginalFilename', 'PathCat.exe')])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])])",
        encoding='utf-8')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                    '--onefile', '--windowed', '--name', 'PathCat',
                    '--distpath', str(output), '--workpath', str(ROOT / 'build'),
                    '--specpath', str(ROOT / 'build'),
                    '--version-file', str(resource),
                    '--add-data', f'{ROOT / "VERSION"};.',
                    '--add-data', f'{ROOT / "quietpet/assets"};quietpet/assets',
                    '--add-data', f'{ROOT / "Cursor_QuietPet_Icons"};Cursor_QuietPet_Icons',
                    str(ROOT / 'PathCat.py')], cwd=ROOT, check=True)
    executable = output / 'PathCat.exe'
    archive = output / f'PathCat-{version}-windows-x64.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(executable, 'PathCat.exe')
        for name in ('README.md', 'VERSION', 'CHANGELOG.md', 'THIRD_PARTY_NOTICES.md'):
            zip_file.write(ROOT / name, name)
        for path in sorted((ROOT / 'docs/media').rglob('*')):
            if path.is_file():
                zip_file.write(path, path.relative_to(ROOT).as_posix())
        for path in sorted((ROOT / 'quietpet/_vendor').rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                zip_file.write(path, path.relative_to(ROOT).as_posix())
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / 'SHA256SUMS.txt').write_text(f'{checksum}  {archive.name}\n', encoding='utf-8')
    print(f'Built {archive.name}; SHA256 {checksum}')


if __name__ == '__main__':
    main()
