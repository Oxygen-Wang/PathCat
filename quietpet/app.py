# -*- coding: utf-8 -*-
"""Application wiring: pet window + explorer panel + global summon gesture."""
import queue
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog

from .core import config
from .core import i18n
from .ui.explorer import Explorer
from .gestures.hotkey import GlobalHotkey, is_tap_gesture, parse_hotkey
from .ui.pet import Pet
from .native.win32 import force_top


class QuietPet:
    def __init__(self):
        self.settings = config.load_settings()
        i18n.set_language(self.settings.get('language') or 'zh')
        self.root = tk.Tk()
        self.root.report_callback_exception = self._log_exception

        self.pet = Pet(self.root, self.settings)
        self.pet.on_click = self.toggle_panel
        self.pet.on_menu = self.pet_menu
        self.pet.on_moved = self.on_pet_moved
        self.pet.on_drag = self.on_pet_drag
        self.pet.on_press = self.on_pet_press
        self.pet.on_drop = self.on_cat_drop

        self.explorer = Explorer(self.root, self.settings, self.pet_pos, self.save)

        self.hotkey_text = (self.settings.get('hotkey') or config.DEFAULT_HOTKEY).strip()
        self.hotkey_queue = queue.Queue()
        self.hotkey_manager = None
        self.hotkey_ok = False
        self._timers = {}

        self.root.bind('<Escape>', lambda e: self.explorer.hide())
        self.pet.enable_drop()
        self.explorer.on_visibility = self.on_panel_visibility
        self.explorer.on_event = self.pet.play
        self.start_hotkey()

        self._tick('hotkey', 150, self.poll_hotkey)
        self._tick('status', 300, self.refresh_status)
        self._tick('raise', 400, self.pet.raise_pet)
        self._tick('dock', 700, self.dock_pet)
        self._tick('periodic', 1500, self.periodic)

    # --- timers ------------------------------------------------------------
    def _tick(self, key, delay, fn):
        """Schedule a recurring callback that is cancelled cleanly on quit."""
        def wrapped():
            self._timers.pop(key, None)
            try:
                fn()
            except tk.TclError:
                return
        self._timers[key] = self.root.after(delay, wrapped)

    def refresh_status(self):
        self.pet.refresh_status()
        self._tick('status', 2000, self.refresh_status)

    def poll_hotkey(self):
        try:
            while True:
                kind, payload = self.hotkey_queue.get_nowait()
                if kind == 'fire':
                    self.on_hotkey()
                elif kind == 'ok':
                    self.hotkey_ok = True
                elif kind == 'error':
                    self.hotkey_ok = False
                    self.root.after(400, lambda h=payload: messagebox.showwarning(
                        i18n.t('hotkey_warn_title'), i18n.t('hotkey_warn', name=h)))
        except queue.Empty:
            pass
        self._tick('hotkey', 150, self.poll_hotkey)

    # --- helpers -----------------------------------------------------------
    def _log_exception(self, exc, val, tb):
        try:
            import traceback
            from datetime import datetime
            with open(config.DATA / 'error.log', 'a', encoding='utf-8') as f:
                f.write(f'--- {datetime.now()}\n')
                traceback.print_exception(exc, val, tb, file=f)
        except Exception:
            pass

    def pet_pos(self):
        return self.root.winfo_x(), self.root.winfo_y()

    def save(self):
        config.save_settings(self.settings)

    def toggle_panel(self):
        self.explorer.toggle()

    def on_cat_drop(self, paths):
        """A folder dropped onto the cat becomes the managed folder."""
        folders = [p for p in paths if Path(p).is_dir()]
        if not folders:
            return
        self.explorer.set_folder(folders[0])
        if not (self.explorer.panel and self.explorer.panel.winfo_exists()
                and self.explorer.panel.state() == 'normal'):
            self.explorer.show()
        else:
            self.explorer.panel.lift()
        self.dock_pet()

    def on_panel_visibility(self):
        visible = (self.explorer.panel and self.explorer.panel.winfo_exists()
                   and self.explorer.panel.state() == 'normal')
        self.pet.play('panel_open' if visible else 'panel_close', ms=700)
        self.root.after(30, self.dock_pet)

    def _panel_visible(self):
        return bool(self.explorer.panel and self.explorer.panel.winfo_exists()
                    and self.explorer.panel.state() == 'normal')

    def _cat_x_for_state(self):
        sw = self.root.winfo_screenwidth()
        side = self.settings.get('panel_side', 'right')
        if self._panel_visible():
            pw = self.explorer.panel_width()
            return (sw - pw) - 80 - 6 if side == 'right' else pw + 6
        return (sw - 80) if side == 'right' else 0

    def on_pet_press(self):
        pass

    def on_pet_drag(self):
        """Live: dragging the cat resizes the sidebar width (cat on the inner edge)."""
        if not self._panel_visible():
            return
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        cat_x = self.root.winfo_x()
        side = 'left' if (cat_x + 40) < sw // 2 else 'right'
        self.settings['panel_side'] = side
        width = (sw - cat_x - 86) if side == 'right' else (cat_x - 6)
        width = max(260, min(width, max(260, sw - 80)))
        self.settings['panel_width'] = width
        self.explorer.position()

    def on_pet_moved(self):
        self._snap_cat()
        self.save()

    def _snap_cat(self):
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x = self._cat_x_for_state()
        y = max(0, min(self.root.winfo_y(), max(0, sh - 98)))
        self.root.geometry(f'80x98+{x}+{y}')
        self.settings.update(x=x, y=y)
        self.pet.raise_pet()

    def dock_pet(self):
        """Closed -> cat at the screen edge; open -> cat on the panel's inner edge."""
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x = self._cat_x_for_state()
        y = max(0, (sh - 98) // 2)
        self.root.geometry(f'80x98+{x}+{y}')
        self.settings.update(x=x, y=y)
        self.save()
        self.pet.raise_pet()

    def pet_menu(self, ev):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=i18n.t('pet_open_panel'), command=self.explorer.show)
        menu.add_command(label=i18n.t('pet_change_folder'), command=self.explorer.choose_folder)
        menu.add_command(label=i18n.t('pet_open_explorer'),
                         command=lambda: self.explorer._open_external(self.explorer.folder))
        menu.add_separator()
        mark = '✓ ' if self.hotkey_ok else '⚠ '
        menu.add_command(label=i18n.t('pet_hotkey', mark=mark, name=self.hotkey_text),
                         command=self.change_hotkey)
        lang = tk.Menu(menu, tearoff=0)
        for code in i18n.available():
            lang.add_command(label=i18n.t('lang_' + code),
                             command=lambda c=code: self.set_language(c))
        menu.add_cascade(label=i18n.t('pet_language'), menu=lang)
        menu.add_separator()
        menu.add_command(label=i18n.t('pet_quit'), command=self.quit)
        menu.tk_popup(ev.x_root, ev.y_root)

    def set_language(self, code):
        i18n.set_language(code)
        self.settings['language'] = code
        self.save()
        self.pet.status_label = i18n.t('status_' + self.pet.status_kind)
        self.pet.draw_status()
        if self.explorer.panel and self.explorer.panel.winfo_exists():
            self.explorer.panel.destroy()
            self.explorer.panel = None
            self.explorer.show()

    # --- hotkey ------------------------------------------------------------
    def start_hotkey(self):
        if not config.IS_WIN or not self.hotkey_text:
            return
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        self.hotkey_manager = GlobalHotkey(self.hotkey_text, self.hotkey_queue)
        self.hotkey_manager.start()

    def on_hotkey(self):
        self.root.deiconify()
        self.root.lift()
        self.pet.raise_pet()
        self.explorer.toggle()
        if self.explorer.panel and self.explorer.panel.winfo_exists() and \
                self.explorer.panel.state() == 'normal':
            self.explorer.panel.lift()
            force_top(self.explorer.panel.winfo_id())
        self.dock_pet()

    def change_hotkey(self):
        text = simpledialog.askstring(
            i18n.t('hotkey_title'), i18n.t('hotkey_prompt'),
            initialvalue=self.hotkey_text or config.DEFAULT_HOTKEY)
        if not text:
            return
        text = text.strip()
        if not is_tap_gesture(text) and parse_hotkey(text) is None:
            messagebox.showerror(i18n.t('hotkey_invalid_title'),
                                 i18n.t('hotkey_invalid', text=text))
            return
        self.hotkey_text = text
        self.settings['hotkey'] = text
        self.save()
        self.hotkey_ok = False
        self.start_hotkey()

    # --- lifecycle ---------------------------------------------------------
    def periodic(self):
        # Do NOT rebuild the tree here: it would move rows out from under the
        # user mid-drag. The tree refreshes on demand and after operations.
        self.pet.raise_pet()
        if (self.explorer.panel and self.explorer.panel.winfo_exists()
                and self.explorer.panel.state() == 'normal'):
            force_top(self.explorer.panel.winfo_id())
        self._tick('periodic', 8000, self.periodic)

    def quit(self):
        self.settings.update(x=self.root.winfo_x(), y=self.root.winfo_y())
        self.save()
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        for after_id in list(self._timers.values()):
            try:
                self.root.after_cancel(after_id)
            except tk.TclError:
                pass
        self._timers.clear()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    QuietPet().run()


if __name__ == '__main__':
    main()
