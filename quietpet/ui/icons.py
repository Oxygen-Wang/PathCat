# -*- coding: utf-8 -*-
"""Load the Cursor-style PNG icon set and recolor it for the dark theme.

Pure standard library: a small 8-bit RGBA PNG decoder (no Pillow) plus a
nearest/box downsample so 64px sources render crisply at 16px.
"""
import struct
import sys
import tkinter as tk
import zlib
from pathlib import Path

ICON_NAMES = ['folder', 'file', 'new-file', 'new-folder', 'refresh',
              'copy', 'search', 'settings', 'mcp']
ICON_DIR_NAME = 'Cursor_QuietPet_Icons'


def resolve_icon_dir():
    """Find the icon pack next to the project, next to a frozen exe, or in cwd."""
    candidates = []
    try:
        candidates.append(Path(__file__).resolve().parent.parent / ICON_DIR_NAME)
    except NameError:
        pass
    if getattr(sys, 'frozen', False):
        candidates.append(Path(sys.executable).resolve().parent / ICON_DIR_NAME)
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            candidates.append(Path(meipass) / ICON_DIR_NAME)
    candidates.append(Path.cwd() / ICON_DIR_NAME)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def decode_png_rgba(path):
    """Decode a non-interlaced 8-bit RGB/RGBA PNG into (width, height, bytes)."""
    data = Path(path).read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG')
    pos = 8
    idat = bytearray()
    width = height = bit_depth = color_type = 0
    while pos + 8 <= len(data):
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        chunk_type = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if chunk_type == b'IHDR':
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack('>IIBBBBB', chunk[:13])
            if bit_depth != 8 or color_type not in (2, 6) or interlace != 0:
                raise ValueError('unsupported PNG (bit depth/color type/interlace)')
        elif chunk_type == b'IDAT':
            idat += chunk
        elif chunk_type == b'IEND':
            break
    raw = zlib.decompress(bytes(idat))
    channels = 4 if color_type == 6 else 3
    stride = width * channels
    out = bytearray(width * height * 4)
    prev = bytearray(stride)
    pos = 0
    for y in range(height):
        ftype = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        if ftype == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        row = y * width * 4
        for x in range(width):
            s = x * channels
            out[row + x * 4] = line[s]
            if channels == 4:
                out[row + x * 4 + 1] = line[s + 1]
                out[row + x * 4 + 2] = line[s + 2]
                out[row + x * 4 + 3] = line[s + 3]
            else:
                out[row + x * 4 + 1] = line[s]
                out[row + x * 4 + 2] = line[s]
                out[row + x * 4 + 3] = 255
        prev = line
    return width, height, bytes(out)


def _resize_alpha(rgba, width, height, size):
    """Box-average the alpha channel down to size x size."""
    factor = max(1, width // size)
    alpha = bytearray(size * size)
    for ty in range(size):
        for tx in range(size):
            total = count = 0
            for dy in range(factor):
                y = ty * factor + dy
                if y >= height:
                    break
                row = y * width * 4
                for dx in range(factor):
                    x = tx * factor + dx
                    if x >= width:
                        break
                    total += rgba[row + x * 4 + 3]
                    count += 1
            alpha[ty * size + tx] = total // count if count else 0
    return alpha


def _to_photo(master, size, alpha, color, threshold=48):
    img = tk.PhotoImage(master=master, width=size, height=size)
    for y in range(size):
        x = 0
        while x < size:
            if alpha[y * size + x] >= threshold:
                start = x
                while x < size and alpha[y * size + x] >= threshold:
                    x += 1
                img.put(color, to=(start, y, x, y + 1))
            else:
                x += 1
    return img


def load_icons(master=None, size=16, color='#cfd3da'):
    """Return {name: PhotoImage} for the icon pack, recolored and resized."""
    base = resolve_icon_dir()
    if not base:
        return {}
    source = base / '64px' if (base / '64px').is_dir() else base / '256px'
    icons = {}
    for name in ICON_NAMES:
        path = source / f'{name}.png'
        if not path.exists():
            continue
        try:
            width, height, rgba = decode_png_rgba(path)
            alpha = _resize_alpha(rgba, width, height, size)
            icons[name] = _to_photo(master, size, alpha, color)
        except Exception:
            continue
    return icons
