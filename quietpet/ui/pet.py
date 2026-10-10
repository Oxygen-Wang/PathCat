# -*- coding: utf-8 -*-
"""The desktop pet window: the cat drawing, dragging and opencode status."""
import tkinter as tk

from ..core import config
from ..core.i18n import t
from ..opencode.status import read_opencode_status
from ..native.win32 import force_top, install_drop_targets


class Pet:
    """Owns the borderless always-on-top cat window."""

    def __init__(self, root, settings):
        self.root = root
        self.settings = settings
        self.status_kind = 'off'
        self.status_label = t('status_off')
        self.drop_targets = []
        self.drag_start = None
        self.was_dragged = False

        # assigned by the application
        self.on_click = lambda: None
        self.on_menu = lambda ev: None
        self.on_moved = lambda: None
        self.on_drag = lambda: None
        self.on_press = lambda: None
        self.on_drop = lambda paths: None

        root.overrideredirect(True)
        root.attributes('-topmost', True)
        root.configure(bg='#ff00ff')
        if config.IS_WIN:
            root.wm_attributes('-transparentcolor', '#ff00ff')
        dw, dh = 80, 98
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        default_x = max(0, sw - dw - 16)          # right edge
        default_y = max(0, (sh - dh) // 2)        # vertically centered
        root.geometry(f"{dw}x{dh}+{settings.get('x', default_x)}+{settings.get('y', default_y)}")

        self.canvas = tk.Canvas(root, width=80, height=98, bg='#ff00ff',
                                bd=0, highlightthickness=0, cursor='hand2')
        self.canvas.pack()
        self.draw_cat()
        self.draw_status()

        self.canvas.bind('<ButtonPress-1>', self._down)
        self.canvas.bind('<B1-Motion>', self._move)
        self.canvas.bind('<ButtonRelease-1>', self._up)
        self.canvas.bind('<Button-3>', lambda e: self.on_menu(e))

    # --- drawing -----------------------------------------------------------
    def draw_cat(self):
        c = self.canvas
        c.delete('all')
        ox, oy = 8, 30
        c.create_oval(11 + ox, 15 + oy, 53 + ox, 57 + oy, fill='#272a30', outline='#777d8a', width=2)
        c.create_polygon(13 + ox, 27 + oy, 12 + ox, 8 + oy, 28 + ox, 19 + oy, fill='#272a30', outline='#777d8a', width=2)
        c.create_polygon(36 + ox, 19 + oy, 52 + ox, 8 + oy, 51 + ox, 27 + oy, fill='#272a30', outline='#777d8a', width=2)
        c.create_oval(22 + ox, 33 + oy, 26 + ox, 38 + oy, fill='#e9e9ec', outline='')
        c.create_oval(38 + ox, 33 + oy, 42 + ox, 38 + oy, fill='#e9e9ec', outline='')
        c.create_polygon(30 + ox, 43 + oy, 34 + ox, 43 + oy, 32 + ox, 46 + oy, fill='#d8a4ac', outline='')
        c.create_text(32 + ox, 65 + oy, text='●', fill='#878d9a', font=('Segoe UI', 8))

    def draw_status(self):
        c = self.canvas
        c.delete('status')
        color = config.STATUS_STYLES.get(self.status_kind, config.STATUS_STYLES['off'])[0]
        label = t('status_' + self.status_kind)
        c.create_rectangle(5, 4, 75, 24, fill='#23252b', outline='#3a3d43', tags='status')
        c.create_oval(11, 10, 19, 18, fill=color, outline='', tags='status')
        c.create_text(24, 14, text=label, anchor='w', fill='#d7dae0', font=('Segoe UI', 8), tags='status')

    # --- behaviour ---------------------------------------------------------
    def raise_pet(self):
        if self.root.winfo_exists():
            force_top(self.root.winfo_id())

    def _down(self, ev):
        self.drag_start = (ev.x_root, ev.y_root, self.root.winfo_x(), self.root.winfo_y())
        self.was_dragged = False
        self.on_press()

    def _move(self, ev):
        if not self.drag_start:
            return
        sx, sy, x, y = self.drag_start
        dx, dy = ev.x_root - sx, ev.y_root - sy
        if abs(dx) + abs(dy) > 5:
            self.was_dragged = True
        self.root.geometry(f'+{max(0,x+dx)}+{max(0,y+dy)}')
        self.on_drag()

    def _up(self, ev):
        self.drag_start = None
        if self.was_dragged:
            self.settings.update(x=self.root.winfo_x(), y=self.root.winfo_y())
            self.on_moved()
        else:
            self.on_click()

    def refresh_status(self):
        result = read_opencode_status()
        if result is not None:
            kind = result[0]
            if kind != self.status_kind:
                self.status_kind = kind
                self.status_label = t('status_' + kind)
                self.draw_status()

    def enable_drop(self):
        install_drop_targets(self.root, self.on_drop, self.drop_targets)
