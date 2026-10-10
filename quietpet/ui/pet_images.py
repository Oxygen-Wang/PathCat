"""Resize pet PNGs and avoid color-key halos without a runtime image library."""
import base64
import struct
import tkinter as tk
import zlib

from .icons import decode_png_rgba


def encode_rgba(width, height, rgba):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    rows = b''.join(b'\0' + rgba[y * width * 4:(y + 1) * width * 4] for y in range(height))
    header = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')


def load_pet_image(master, path, scale=100):
    width, height, rgba = decode_png_rgba(path)
    limit = max(1, round(64 * scale / 100))
    ratio = limit / max(width, height)
    tw, th = max(1, round(width * ratio)), max(1, round(height * ratio))
    out = bytearray(tw * th * 4)
    for y in range(th):
        sy = max(0, min(height - 1, (y + .5) * height / th - .5))
        y0, y1 = int(sy), min(height - 1, int(sy) + 1)
        fy = sy - y0
        for x in range(tw):
            sx = max(0, min(width - 1, (x + .5) * width / tw - .5))
            x0, x1 = int(sx), min(width - 1, int(sx) + 1)
            fx = sx - x0
            samples = [(x0, y0, (1-fx)*(1-fy)), (x1, y0, fx*(1-fy)),
                       (x0, y1, (1-fx)*fy), (x1, y1, fx*fy)]
            alpha = 0
            color = [0., 0., 0.]
            for px, py, weight in samples:
                offset = (py * width + px) * 4
                contribution = rgba[offset + 3] * weight
                alpha += contribution
                for channel in range(3):
                    color[channel] += rgba[offset + channel] * contribution
            # Tk blends partial alpha into magenta before Windows removes
            # the exact color key. Binary alpha prevents that pink fringe.
            if alpha >= 96:
                offset = (y * tw + x) * 4
                out[offset:offset + 4] = bytes([round(c / alpha) for c in color] + [255])
    data = base64.b64encode(encode_rgba(tw, th, bytes(out)))
    return tk.PhotoImage(master=master, data=data)
