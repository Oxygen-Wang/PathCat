"""A dismissible onboarding bubble anchored above the desktop cat."""
import tkinter as tk

from ..core import config, i18n


def should_show(settings):
    return False


class Tutorial:
    STEPS = ('tutorial_open', 'tutorial_folder', 'tutorial_drag', 'tutorial_settings')

    def __init__(self, root, settings, save):
        self.root, self.settings, self.save = root, settings, save
        self.window = None
        self.step = 0
        self._position_job = None
        root.bind('<Configure>', self._on_move, add='+')

    def start(self):
        self.step = 0
        self.render()

    def render(self):
        # Reuse the bubble: destroying the active window on every Next click
        # can activate another application and put the non-topmost cat behind it.
        if self.window is None:
            self.window = tk.Toplevel(self.root)
            self.window.withdraw()
            self.window.overrideredirect(True)
            self.window.attributes('-topmost', False)
        window = self.window
        for child in window.winfo_children():
            child.destroy()
        window.configure(bg=config.BTN_HOVER)
        body = tk.Frame(window, bg=config.BG, padx=12, pady=10)
        body.pack(padx=1, pady=1)
        tk.Label(body, text=i18n.t('tutorial_title', current=self.step + 1,
                                total=len(self.STEPS)), bg=config.BG, fg=config.FG,
                 font=config.ui_font(10, 'bold')).pack(anchor='w')
        tk.Label(body, text=i18n.t(self.STEPS[self.step], hotkey=self.settings.get(
            'hotkey', config.DEFAULT_HOTKEY)), wraplength=280, justify='left',
            bg=config.BG, fg=config.FG, font=config.ui_font(), pady=8).pack(anchor='w')
        actions = tk.Frame(body, bg=config.BG)
        actions.pack(fill='x')
        tk.Button(actions, text=i18n.t('tutorial_skip'), command=self.finish,
                  bg=config.BTN, fg=config.FG, font=config.ui_font(9),
                  activebackground=config.BTN_HOVER, activeforeground=config.FG,
                  relief='flat').pack(side='left')
        tk.Button(actions, text=i18n.t('tutorial_done' if self.step == len(self.STEPS) - 1
                                      else 'tutorial_next'), command=self.next,
                  bg=config.SEL, fg=config.SEL_FG, font=config.ui_font(9),
                  activebackground=config.BTN_HOVER, activeforeground=config.FG,
                  relief='flat').pack(side='right')
        window.update_idletasks()
        self.position()
        window.deiconify()
        # Keep both windows visible for this user interaction, without pinning
        # either above other applications after the user switches away.
        self.root.deiconify()
        self.root.lift()
        window.lift(self.root)

    def next(self):
        if self.step + 1 == len(self.STEPS):
            self.finish()
        else:
            self.step += 1
            self.render()

    def finish(self):
        self.close()
        self.root.deiconify()
        self.root.lift()
        self.settings['tutorial_complete'] = True
        self.save()

    def close(self):
        if self._position_job is not None:
            self.root.after_cancel(self._position_job)
            self._position_job = None
        if self.window is not None:
            self.window.destroy()
            self.window = None

    def _on_move(self, event):
        if event.widget is self.root and self.window is not None and self._position_job is None:
            self._position_job = self.root.after_idle(self.position)

    def position(self):
        self._position_job = None
        if self.window is None:
            return
        w, h = self.window.winfo_reqwidth(), self.window.winfo_reqheight()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x = max(0, min(self.root.winfo_x() + self.root.winfo_width() // 2 - w // 2, sw - w))
        y = self.root.winfo_y() - h - 6
        if y < 0:
            y = self.root.winfo_y() + self.root.winfo_height() + 6
        y = max(0, min(y, sh - h))
        self.window.geometry(f'+{x}+{y}')
