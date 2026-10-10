# -*- coding: utf-8 -*-
"""The desktop pet window: cat rendering (image states + animation) and status."""
import json
import tkinter as tk
import time
from pathlib import Path

from ..core import config
from ..core.i18n import t
from ..native.win32 import install_drop_targets

CAT_DIR = Path(__file__).resolve().parent.parent / 'assets' / 'cat'
BASE_STATES = ('idle', 'working', 'waiting', 'offline')
IDLE_SLEEP_SECONDS = 5 * 60
CAT_SKINS = ('default', 'calico')
HOVER_OPEN_MS = 500
CAT_SCALES = (75, 100, 150, 200)


class Pet:
    """Owns the borderless cat window in the normal desktop window layer."""

    def __init__(self, root, settings):
        self.root = root
        self.settings = settings
        self.status_kind = 'idle'
        self.status_label = t('status_idle')
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
        self.on_hover = lambda: None

        # image state machine
        self.manifest = {}
        self.frame_ms = 120
        self.base_state = 'idle'
        self.state = 'idle'
        self._frames = {}
        self._anim_index = 0
        self._anim_after = None
        self._revert_after = None
        self._file_drag_window = None
        self._file_drag_image = None
        self._file_drag_alpha = None
        self._last_activity = time.monotonic()
        self.sleeping = False
        self._awake_base_state = 'idle'
        self.skin = self.settings.get('cat_skin', 'default')
        if self.skin not in CAT_SKINS:
            self.skin = 'default'
        self.asset_dir = CAT_DIR if self.skin == 'default' else CAT_DIR / self.skin
        self._hover_after = None
        self.scale = self.settings.get('cat_scale', 100)
        if self.scale not in CAT_SCALES:
            self.scale = 100
        self._load_manifest()

        root.overrideredirect(True)
        root.attributes('-topmost', True)
        root.configure(bg='#ff00ff')
        if config.IS_WIN:
            root.wm_attributes('-transparentcolor', '#ff00ff')
        dw, dh = self.window_size
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
            data = json.loads((self.asset_dir / 'manifest.json').read_text(encoding='utf-8'))
            self.manifest = data.get('states', {})
            self.frame_ms = int(data.get('frame_ms', 120))
        except Exception:
            self.manifest = {}

    def _state_frames(self, name):
        if name not in self.manifest:
            return []
        if name not in self._frames:
            frames = []
            entry = self.manifest[name]
            for rel in entry.get('frames', []) + entry.get('optional_frames', []):
                try:
                    from .pet_images import load_pet_image
                    frames.append(load_pet_image(self.root, self.asset_dir / rel, self.scale))
                except Exception:
                    pass
            self._frames[name] = frames
        return self._frames[name]

    def _display_frames(self, name):
        """Missing action artwork uses the default character, then Tk shapes."""
        return self._state_frames(name) or self._state_frames('idle')

    def set_skin(self, name):
        if name not in CAT_SKINS:
            return
        self.follow_file_drag(None)
        if self._file_drag_window is not None:
            self._file_drag_window.destroy()
            self._file_drag_window = None
            self._file_drag_image = None
        self.skin = name
        self.settings['cat_skin'] = name
        self.asset_dir = CAT_DIR if name == 'default' else CAT_DIR / name
        self._frames.clear()
        self._load_manifest()
        self.note_activity()
        self.draw_cat()
        self._start_anim()

    @property
    def window_size(self):
        return round(80 * self.scale / 100), round(98 * self.scale / 100)

    def set_scale(self, scale):
        if scale not in CAT_SCALES:
            return
        self.scale = scale
        self.settings['cat_scale'] = scale
        self.set_skin(self.skin)
        w, h = self.window_size
        self.canvas.configure(width=w, height=h)
        self.root.geometry(f'{w}x{h}')
        self.draw_cat()

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
        self.note_activity()
        self.set_state(name, transient=True, ms=ms)

    def note_activity(self, _event=None):
        """Interaction wakes the pet and restarts its inactivity interval."""
        self._last_activity = time.monotonic()
        if self.sleeping:
            self.sleeping = False
            self.base_state = self._awake_base_state
            self.set_state(self.base_state)

    def check_inactivity(self):
        if (not self.sleeping and self.drag_start is None
                and self._file_drag_alpha is None
                and time.monotonic() - self._last_activity >= IDLE_SLEEP_SECONDS):
            self._awake_base_state = self.base_state
            self.sleeping = True
            self.base_state = 'sleeping'
            self.set_state('sleeping')

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
        if len(self._display_frames(self.state)) > 1:
            self._anim_after = self.root.after(self.frame_ms, self._anim_tick)

    def _anim_tick(self):
        self._anim_after = None
        frames = self._display_frames(self.state)
        if len(frames) > 1:
            self._anim_index = (self._anim_index + 1) % len(frames)
            self.draw_cat()
            self._anim_after = self.root.after(self.frame_ms, self._anim_tick)

    # --- drawing -----------------------------------------------------------
    def draw_cat(self):
        self._draw_character(self.canvas, self.state, self._anim_index)

    def _draw_character(self, c, state, index=0):
        c.delete('cat')
        frames = self._display_frames(state)
        if frames:
            c.create_image(self.window_size[0] // 2, round(64 * self.scale / 100),
                           image=frames[index % len(frames)], tags='cat')
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
        c.scale('cat', 0, 0, self.scale / 100, self.scale / 100)

    def draw_status(self):
        # Head space is reserved for onboarding. Task state stays in animation
        # and the file panel, without a permanent conversation/status bubble.
        self.canvas.delete('status')

    # --- status ------------------------------------------------------------

    # --- behaviour ---------------------------------------------------------
    def raise_pet(self):
        if self.root.winfo_exists():
            self.root.lift()

    def _enter(self, _ev=None):
        self.note_activity()
        self._cancel_hover()
        if self.drag_start is None and self._file_drag_alpha is None:
            self._hover_after = self.root.after(HOVER_OPEN_MS, self._hover_open)
        if not self.was_dragged and self.state not in ('dragging', 'dropped'):
            self.set_state('hover')

    def _leave(self, _ev=None):
        self._cancel_hover()
        if self.state in ('hover',):
            self.set_state(self.base_state)

    def _down(self, ev):
        self._cancel_hover()
        self.note_activity()
        self.drag_start = (ev.x_root, ev.y_root, self.root.winfo_x(), self.root.winfo_y())
        self.was_dragged = False
        self.on_press()

    def _cancel_hover(self):
        if self._hover_after is not None:
            self.root.after_cancel(self._hover_after)
            self._hover_after = None

    def _hover_open(self):
        self._hover_after = None
        if self.drag_start is None and self._file_drag_alpha is None:
            self.on_hover()

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

    def follow_file_drag(self, point):
        """Show a click-through companion without changing the dock position."""
        if point is None:
            if self._file_drag_window is not None:
                self._file_drag_window.withdraw()
            if self._file_drag_alpha is not None:
                self.root.attributes('-alpha', self._file_drag_alpha)
                self._file_drag_alpha = None
            return
        self.note_activity()
        if self._file_drag_window is None:
            from ..native.win32 import make_drag_overlay_clickthrough
            # Only the empty-handed action is eligible. The old sprite has a
            # folder baked into it and cannot be used for independent icons.
            frames = self._display_frames('file_drag')
            self._file_drag_image = frames[0] if frames else None
            tip = tk.Toplevel(self.root)
            tip.withdraw()
            tip.overrideredirect(True)
            tip.configure(bg='#ff00ff')
            if config.IS_WIN:
                tip.wm_attributes('-transparentcolor', '#ff00ff')
            tip.attributes('-topmost', True)
            w, h = self.window_size
            canvas = tk.Canvas(tip, width=w, height=h, bg='#ff00ff',
                               bd=0, highlightthickness=0)
            canvas.pack()
            self._draw_character(canvas, 'file_drag')
            tip.update_idletasks()
            make_drag_overlay_clickthrough(tip.winfo_id())
            self._file_drag_window = tip
        if self._file_drag_alpha is None:
            self._file_drag_alpha = self.root.attributes('-alpha')
            self.root.attributes('-alpha', 0)
        x, y = point
        w, h = self.window_size
        # Leave the actual drop point clear, including at the screen edges.
        px, py = x - w // 2, y + 24
        if py + h > self.root.winfo_screenheight():
            py = y - h - 24
        px = max(0, min(px, self.root.winfo_screenwidth() - w))
        py = max(0, py)
        self._file_drag_window.geometry(f'{w}x{h}{px:+d}{py:+d}')
        self._file_drag_window.deiconify()
        self._file_drag_window.update_idletasks()
