# -*- coding: utf-8 -*-
"""The desktop pet window: cat rendering (image states + animation) and status."""
import json
import tkinter as tk
from pathlib import Path

from ..core import config
from ..core.i18n import t
from ..opencode.status import read_opencode_status
from ..native.win32 import force_top, install_drop_targets

CAT_DIR = Path(__file__).resolve().parent.parent / 'assets' / 'cat'
BASE_STATES = ('idle', 'working', 'waiting', 'offline')


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

        # image state machine
        self.manifest = {}
        self.frame_ms = 120
        self.base_state = 'idle'
        self.state = 'idle'
        self._frames = {}
        self._anim_index = 0
        self._anim_after = None
        self._revert_after = None
        self._load_manifest()

        root.overrideredirect(True)
        root.attributes('-topmost', True)
        root.configure(bg='#ff00ff')
        if config.IS_WIN:
            root.wm_attributes('-transparentcolor', '#ff00ff')
        dw, dh = 80, 98
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        default_x = max(0, sw - dw - 16)
        default_y = max(0, (sh - dh) // 2)
        root.geometry(f"{dw}x{dh}+{settings.get('x', default_x)}+{settings.get('y', default_y)}")

        self.canvas = tk.Canvas(root, width=dw, height=dh, bg='#ff00ff',
                                bd=0, highlightthickness=0, cursor='hand2')
        self.canvas.pack()
        self.draw_cat()
        self.draw_status()

        self.canvas.bind('<ButtonPress-1>', self._down)
        self.canvas.bind('<B1-Motion>', self._move)
        self.canvas.bind('<ButtonRelease-1>', self._up)
        self.canvas.bind('<Button-3>', lambda e: self.on_menu(e))
        self.canvas.bind('<Enter>', self._enter)
        self.canvas.bind('<Leave>', self._leave)

    # --- image states ------------------------------------------------------
    def _load_manifest(self):
        try:
            data = json.loads((CAT_DIR / 'manifest.json').read_text(encoding='utf-8'))
            self.manifest = data.get('states', {})
            self.frame_ms = int(data.get('frame_ms', 120))
        except Exception:
            self.manifest = {}

    def _state_frames(self, name):
        if name not in self.manifest:
            return []
        if name not in self._frames:
            frames = []
            for rel in self.manifest[name].get('frames', []):
                try:
                    frames.append(tk.PhotoImage(master=self.root, file=str(CAT_DIR / rel)))
                except Exception:
                    pass
            self._frames[name] = frames
        return self._frames[name]

    def set_state(self, name, transient=False, ms=900):
        """Switch the cat's picture. Non-looping states revert to the base state."""
        if not self.manifest or name not in self.manifest:
            return
        if self._revert_after:
            try:
                self.root.after_cancel(self._revert_after)
            except tk.TclError:
                pass
            self._revert_after = None
        self.state = name
        self._anim_index = 0
        self.draw_cat()
        self._start_anim()
        if transient or not self.manifest[name].get('loop', False):
            self._revert_after = self.root.after(ms, self._revert)

    def play(self, name, ms=900):
        self.set_state(name, transient=True, ms=ms)

    def _revert(self):
        self._revert_after = None
        self.state = self.base_state
        self._anim_index = 0
        self.draw_cat()
        self._start_anim()

    def _start_anim(self):
        if self._anim_after:
            try:
                self.root.after_cancel(self._anim_after)
            except tk.TclError:
                pass
            self._anim_after = None
        if len(self._state_frames(self.state)) > 1:
            self._anim_after = self.root.after(self.frame_ms, self._anim_tick)

    def _anim_tick(self):
        self._anim_after = None
        frames = self._state_frames(self.state)
        if len(frames) > 1:
            self._anim_index = (self._anim_index + 1) % len(frames)
            self.draw_cat()
            self._anim_after = self.root.after(self.frame_ms, self._anim_tick)

    # --- drawing -----------------------------------------------------------
    def draw_cat(self):
        c = self.canvas
        c.delete('cat')
        frames = self._state_frames(self.state)
        if frames:
            c.create_image(40, 64, image=frames[self._anim_index % len(frames)], tags='cat')
            return
        # Fallback: little monochrome cat drawn with Tk (no image assets).
        ox, oy = 8, 30
        c.create_oval(11 + ox, 15 + oy, 53 + ox, 57 + oy, fill='#272a30', outline='#777d8a', width=2, tags='cat')
        c.create_polygon(13 + ox, 27 + oy, 12 + ox, 8 + oy, 28 + ox, 19 + oy, fill='#272a30', outline='#777d8a', width=2, tags='cat')
        c.create_polygon(36 + ox, 19 + oy, 52 + ox, 8 + oy, 51 + ox, 27 + oy, fill='#272a30', outline='#777d8a', width=2, tags='cat')
        c.create_oval(22 + ox, 33 + oy, 26 + ox, 38 + oy, fill='#e9e9ec', outline='', tags='cat')
        c.create_oval(38 + ox, 33 + oy, 42 + ox, 38 + oy, fill='#e9e9ec', outline='', tags='cat')
        c.create_polygon(30 + ox, 43 + oy, 34 + ox, 43 + oy, 32 + ox, 46 + oy, fill='#d8a4ac', outline='', tags='cat')
        c.create_text(32 + ox, 65 + oy, text='●', fill='#878d9a', font=('Segoe UI', 8), tags='cat')

    def draw_status(self):
        c = self.canvas
        c.delete('status')
        color = config.STATUS_STYLES.get(self.status_kind, config.STATUS_STYLES['off'])[0]
        label = t('status_' + self.status_kind)
        c.create_rectangle(5, 4, 75, 24, fill='#23252b', outline='#3a3d43', tags='status')
        c.create_oval(11, 10, 19, 18, fill=color, outline='', tags='status')
        c.create_text(24, 14, text=label, anchor='w', fill='#d7dae0', font=('Segoe UI', 8), tags='status')

    # --- status ------------------------------------------------------------
    def refresh_status(self):
        result = read_opencode_status()
        if result is None:
            return
        kind = result[0]
        self.status_kind = kind
        self.status_label = t('status_' + kind)
        self.draw_status()
        self.base_state = kind if kind in BASE_STATES else 'idle'
        if self.state in BASE_STATES:
            self.set_state(self.base_state)

    # --- behaviour ---------------------------------------------------------
    def raise_pet(self):
        if self.root.winfo_exists():
            force_top(self.root.winfo_id())

    def _enter(self, _ev=None):
        if not self.was_dragged and self.state not in ('dragging', 'dropped'):
            self.set_state('hover')

    def _leave(self, _ev=None):
        if self.state in ('hover',):
            self.set_state(self.base_state)

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
            if not self.was_dragged:
                self.was_dragged = True
                self.set_state('dragging')
        self.root.geometry(f'+{max(0,x+dx)}+{max(0,y+dy)}')
        self.on_drag()

    def _up(self, ev):
        self.drag_start = None
        if self.was_dragged:
            self.play('dropped', ms=700)
            self.on_moved()
        else:
            self.play('click', ms=450)
            self.on_click()

    def enable_drop(self):
        install_drop_targets(self.root, self.on_drop, self.drop_targets)
