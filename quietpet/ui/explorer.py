# -*- coding: utf-8 -*-
"""The file sidebar: lazy tree, clipboard and cross-path drag/copy/move."""
import os
import time
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, simpledialog, messagebox

from ..core import config
from ..core.i18n import t
from .icons import load_icons
from ..core.util import safe_name, unique_dest
from ..core.ignore import (project_ignored, read_ignore_lines, write_ignore_lines,
                           transfer_allowed, top_level_paths, escape_pattern)
from .widgets import ToolTip
from ..native.win32 import (get_cursor_pos, install_drop_targets,
                            left_button_down, register_drop_target, start_ole_drag)
from ..native.win32 import revoke_drop_target

CAT_W = 80          # cat window width
CAT_GAP = 6


class Explorer:
    def __init__(self, root, settings, get_pet_pos, save_settings):
        self.root = root
        self.settings = settings
        self.get_pet_pos = get_pet_pos
        self.save = save_settings

        self.panel = None
        self.inner = None
        self.tree = None
        self.icons = {}
        self.tips = []
        self.drop_targets = []
        self.loaded = set()
        self.clip = None
        self.on_event = lambda name, ms=900: None
        self._drag_event = None
        self._press_xy = None
        self._drag_moved = False
        self._drag_hover = None
        self._drag_hover_since = 0
        self._drag_scroll_at = 0
        self._root_chips = {}
        self._root_style_key = None
        self._drag_root = None
        self._drag_root_since = 0
        self._drag_preview = None
        self.show_ignored = False


        self._press_iid = None
        self._drag_items = None
        self._drag_text = None
        self._drag_active = False
        self._watch_after = None
        self._chip_ref = None
        self._chip_press_xy = None
        self._chip_started = False
        self._row_tip = None
        self._row_after = None
        self._row_iid = None
        self._expand_state = False
        self.toggle_btn = None
        self.on_visibility = lambda: None

        roots = []
        for r in (settings.get('roots') or []):
            if Path(r).is_dir():
                roots.append(str(Path(r)))
        active = settings.get('folder')
        if active and Path(active).is_dir() and str(Path(active)) not in roots:
            roots.insert(0, str(Path(active)))
        if not roots:
            try:
                config.DEFAULT_FOLDER.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
            roots = [str(config.DEFAULT_FOLDER)]
        self.roots = roots
        self.folder = Path(active) if (active and Path(active).is_dir()) else Path(roots[0])
        self.roots_bar = None

    # --- window ------------------------------------------------------------
    def toggle(self):
        if self.panel and self.panel.winfo_exists() and self.panel.state() == 'normal':
            self.hide()
        else:
            self.show()

    def recreate(self):
        """Rebuild theme/language without reopening a hidden panel or losing selection."""
        if not self.panel or not self.panel.winfo_exists():
            return
        visible = self.panel.state() == 'normal'
        opened = self._opened_paths()
        selected = self.tree.selection()
        self._cancel_watch()
        self._hide_row_tip()
        for tip in self.tips:
            tip._hide()
        revoke_drop_target(self.panel.winfo_id())
        revoke_drop_target(self.tree.winfo_id())
        self.panel.destroy()
        self.panel = None
        self.tree = None
        self.show()
        for path in sorted(opened, key=len):
            self._expand_to(path)
        self.tree.selection_set([iid for iid in selected if self.tree.exists(iid)])
        if not visible:
            self.hide()

    def show(self):
        if self.panel and self.panel.winfo_exists():
            self.panel.deiconify()
            self.position()
            self.panel.lift()
            self.update_labels()
            self.rebuild(preserve=False)
            self.on_visibility()
            return
        w = tk.Toplevel(self.root)
        self.panel = w
        w.title(t('panel_title'))
        w.configure(bg=config.BG)
        w.overrideredirect(True)
        w.attributes('-topmost', False)
        w.protocol('WM_DELETE_WINDOW', self.hide)
        self.icons = load_icons(master=self.root, size=16, color=config.FG)
        self.tips = []

        self.inner = tk.Frame(w, bg=config.BG)
        self.inner.pack(fill='both', expand=True, padx=(8, 8))
        self.position()

        top = tk.Frame(self.inner, bg=config.BG)
        top.pack(fill='x', padx=10, pady=(10, 4))
        self._button(top, '×', self.hide, small=True, tip=t('close')).pack(side='right')
        self.roots_bar = tk.Frame(top, bg=config.BG)
        self.roots_bar.pack(side='left', fill='x', expand=True)
        self._build_roots_bar()

        toolbar = tk.Frame(self.inner, bg=config.BG)
        toolbar.pack(fill='x', padx=12, pady=(0, 8))
        for icon_name, fallback, tip, cb in [
                ('folder', '📂', 'tip_open_folder', self.choose_folder),
                ('new-folder', '＋🗂', 'tip_new_folder', self.new_folder),
                ('new-file', '＋📄', 'tip_new_file', self.import_files),
                ('refresh', '↻', 'tip_refresh', lambda: self.rebuild(preserve=True))]:
            self._icon_button(toolbar, icon_name, fallback, cb, tip=t(tip)).pack(side='left', padx=2)
        self.toggle_btn = tk.Button(toolbar, text='⊞', command=self.toggle_expand,
                                    bg=config.BTN, fg=config.FG, activebackground=config.BTN_HOVER,
                                    activeforeground=config.FG, relief='flat', borderwidth=0,
                                    padx=8, pady=3, cursor='hand2', font=config.ui_font(11),
                                    highlightthickness=0)
        self.toggle_btn.pack(side='left', padx=2)
        self.tips.append(ToolTip(self.toggle_btn, t('tip_expand_all')))
        self._button(toolbar, '⚙', self.edit_ignore, small=True,
                     tip=t('ignore_title')).pack(side='left', padx=2)

        style = ttk.Style(w)
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure('Quiet.Treeview', background=config.BG, fieldbackground=config.BG,
                        foreground=config.FG, borderwidth=0, rowheight=max(27, config.FONT_SIZE * 2 + 8), font=config.ui_font(10))
        style.map('Quiet.Treeview', background=[('selected', config.SEL)],
                  foreground=[('selected', config.SEL_FG)])

        body = tk.Frame(self.inner, bg=config.BG)
        tree = ttk.Treeview(body, show='tree', style='Quiet.Treeview', selectmode='extended')
        self.tree = tree
        tree.tag_configure('drop_target', background=config.DROP_BG)
        bar = ttk.Scrollbar(body, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=bar.set)
        tree.pack(side='left', fill='both', expand=True)
        bar.pack(side='right', fill='y')
        tree.bind('<Double-1>', self.on_double)
        tree.bind('<Button-3>', self.context_menu)
        tree.bind('<ButtonPress-1>', self.drag_start)
        tree.bind('<ButtonRelease-1>', self.drag_end)
        tree.bind('<Escape>', self.cancel_drag)
        tree.bind('<<TreeviewOpen>>', self.on_open)
        tree.bind('<Control-c>', lambda e: self.copy_selection())
        tree.bind('<Control-x>', lambda e: self.cut_selection())
        tree.bind('<Control-v>', lambda e: self.paste())
        tree.bind('<F2>', lambda e: self.rename())
        tree.bind('<Delete>', lambda e: self.soft_delete())
        tree.bind('<Motion>', self._row_hover, add='+')
        tree.bind('<Leave>', lambda e: self._hide_row_tip(), add='+')

        footer = tk.Label(self.inner, text=t('footer'),
                          bg=config.BG, fg=config.MUTED, font=config.ui_font(9), anchor='w')
        footer.pack(side='bottom', fill='x', padx=14, pady=10)

        body.pack(fill='both', expand=True, padx=(8, 6))

        self.update_labels()
        self.rebuild(preserve=False)
        if not register_drop_target(w.winfo_id(), self._on_panel_drop) and \
                not register_drop_target(tree.winfo_id(), self._on_panel_drop):
            install_drop_targets(w, self.on_os_drop, self.drop_targets)
        w.lift()
        try:
            w.focus_force()
        except tk.TclError:
            pass
        self.on_visibility()

    def position(self):
        """Dock the panel to the chosen screen edge, full height (sidebar)."""
        if not self.panel or not self.panel.winfo_exists():
            return
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        pw = self.panel_width()
        side = self.settings.get('panel_side', 'right')
        x = sw - pw if side == 'right' else 0
        self.panel.geometry(f'{pw}x{sh}+{x}+0')

    def panel_width(self):
        sw = self.root.winfo_screenwidth()
        pw = int(self.settings.get('panel_width') or 340)
        return max(260, min(pw, max(260, sw - 80)))

    def set_side(self, side):
        side = 'left' if side == 'left' else 'right'
        if self.settings.get('panel_side') != side:
            self.settings['panel_side'] = side
            self.save()
        self.position()

    def hide(self):
        if self.panel and self.panel.winfo_exists():
            self.panel.withdraw()
        self.on_visibility()

    def update_labels(self):
        name = self.folder.name or str(self.folder)
        if self.panel and self.panel.winfo_exists():
            self.panel.title(f'{config.APP} · {name}')
        if self.roots_bar is not None and self.roots_bar.winfo_exists():
            self._build_roots_bar()

    def _build_roots_bar(self):
        for child in self.roots_bar.winfo_children():
            child.destroy()
        active = str(self.folder)
        self._root_chips = {}
        self._root_style_key = None
        for root in self.roots:
            selected = str(Path(root)) == active
            bg = config.SEL if selected else config.BTN
            chip = tk.Frame(self.roots_bar, bg=bg)
            name = Path(root).name or str(root)
            label = tk.Label(chip, text=name, bg=bg, fg=config.SEL_FG if selected else config.FG, padx=7, pady=2,
                             font=config.ui_font(9), cursor='hand2')
            label.pack(side='left')
            close = tk.Label(chip, text='×', bg=bg, fg=config.MUTED, padx=2, pady=2,
                             font=config.ui_font(9), cursor='hand2')
            close.pack(side='left')
            label.bind('<Button-1>', lambda e, r=root: self.set_folder(r))
            close.bind('<Button-1>', lambda e, r=root: self.remove_root(r))
            chip.pack(side='left', padx=2)
            self._root_chips[str(root)] = chip
            self.tips.append(ToolTip(chip, str(root)))
        add = tk.Label(self.roots_bar, text='＋', bg=config.BTN, fg=config.FG, padx=7, pady=2,
                       font=config.ui_font(10, 'bold'), cursor='hand2')
        add.pack(side='left', padx=2)
        add.bind('<Button-1>', lambda e: self.add_root())
        self.tips.append(ToolTip(add, t('add_path')))

    def _button(self, parent, label, command, small=False, tip=None):
        btn = tk.Button(parent, text=label, command=command, bg=config.BTN, fg=config.FG,
                        activebackground=config.BTN_HOVER, activeforeground=config.FG, relief='flat',
                        padx=6 if small else 8, pady=3 if small else 5, cursor='hand2',
                        borderwidth=0, font=config.ui_font(9), highlightthickness=0)
        if tip:
            self.tips.append(ToolTip(btn, tip))
        return btn

    def _icon_button(self, parent, icon_name, fallback, command, tip=None):
        icon = self.icons.get(icon_name) if icon_name else None
        if icon is None:
            return self._button(parent, fallback, command, tip=tip)
        btn = tk.Button(parent, image=icon, command=command, bg=config.BTN,
                        activebackground=config.BTN_HOVER, relief='flat', borderwidth=0,
                        padx=4, pady=4, cursor='hand2', highlightthickness=0)
        if tip:
            self.tips.append(ToolTip(btn, tip))
        return btn

    # --- folder selection --------------------------------------------------
    def choose_folder(self):
        chosen = filedialog.askdirectory(parent=self.panel, title=t('choose_folder_title'),
                                         initialdir=str(self.folder), mustexist=True)
        if chosen:
            self.set_folder(chosen)

    def add_root(self):
        chosen = filedialog.askdirectory(parent=self.panel, title=t('choose_folder_title'),
                                         initialdir=str(self.folder), mustexist=True)
        if chosen:
            self.set_folder(chosen)

    def remove_root(self, path):
        key = str(Path(path))
        if key not in self.roots or len(self.roots) <= 1:
            return
        self.roots.remove(key)
        if str(self.folder) == key:
            self.folder = Path(self.roots[0])
        self.settings['roots'] = self.roots
        self.settings['folder'] = str(self.folder)
        self.save()
        self.loaded = set()
        self.update_labels()
        self.rebuild(preserve=False)

    def set_folder(self, path):
        path = Path(path)
        if not path.is_dir():
            return
        key = str(path)
        if key not in self.roots:
            self.roots.append(key)
        self.folder = path
        self.settings['folder'] = key
        self.settings['roots'] = self.roots
        self.save()
        self.loaded = set()
        self.update_labels()
        self.rebuild(preserve=False)


    def on_os_drop(self, paths):
        self._copy_paths([Path(p) for p in paths], self.target_dir())
        self.on_event('file_in')
        self.rebuild(preserve=True)

    # --- tree model --------------------------------------------------------
    def icon(self, p):
        if self.icons or p.is_dir():
            return ''
        return config.FILE_ICONS.get(p.suffix.lower(), '📄') + ' '

    @staticmethod
    def _short(text, limit=60):
        text = ' '.join(str(text).split())
        return text if len(text) <= limit else text[:limit - 1] + '…'

    def path_of(self, iid):
        if not iid or iid.endswith(config.PLACEHOLDER):
            return None
        return Path(iid)

    def _insert(self, parent, iid, text, image_name=None, open=False):
        kwargs = {'text': text, 'open': open}
        if image_name and image_name in self.icons:
            kwargs['image'] = self.icons[image_name]
        self.tree.insert(parent, 'end', iid=iid, **kwargs)

    def selected_paths(self):
        return [p for p in (self.path_of(i) for i in self.tree.selection()) if p is not None]

    def selected(self):
        if not self.tree:
            return self.folder
        paths = self.selected_paths()
        return paths[0] if paths else self.folder

    def target_dir(self):
        paths = self.selected_paths()
        if paths:
            p = paths[0]
            return p if p.is_dir() else p.parent
        return self.folder

    def inside(self, path):
        try:
            p = Path(path).resolve()
            root = self.folder.resolve()
        except OSError:
            return False
        return p == root or root in p.parents

    def _populate(self, parent_id, directory):
        try:
            entries = [p for p in directory.iterdir() if p.name != config.TRASH and
                       (self.show_ignored or not project_ignored(p, self.folder))]
        except (OSError, PermissionError):
            return
        entries.sort(key=lambda p: (not p.is_dir(), p.name.casefold()))
        for p in entries:
            iid = str(p)
            if self.tree.exists(iid):
                continue
            text = f'{self.icon(p)}{p.name}'
            try:
                if p.is_dir() and not p.is_symlink():
                    self._insert(parent_id, iid, text, 'folder', open=False)
                    self.tree.insert(iid, 'end', iid=iid + config.PLACEHOLDER, text='')
                else:
                    self._insert(parent_id, iid, text, 'file')
            except tk.TclError:
                continue


    def _ensure_loaded(self, iid):
        if iid in self.loaded:
            return
        self.loaded.add(iid)
        for child in self.tree.get_children(iid):
            self.tree.delete(child)
        if iid.startswith('__'):
            return
        self._populate(iid, Path(iid))

    def _opened_paths(self):
        opened = set()

        def walk(item):
            if self.tree.item(item, 'open') and not item.endswith(config.PLACEHOLDER):
                opened.add(item)
            for child in self.tree.get_children(item):
                if not child.endswith(config.PLACEHOLDER):
                    walk(child)

        for item in self.tree.get_children():
            walk(item)
        return opened

    def _expand_to(self, path_str):
        chain = []
        cur = Path(path_str)
        while True:
            chain.append(cur)
            if cur == self.folder or cur.parent == cur:
                break
            cur = cur.parent
        for node in reversed(chain):
            iid = str(node)
            if not self.tree.exists(iid):
                continue
            self._ensure_loaded(iid)
            self.tree.item(iid, open=True)

    def rebuild(self, preserve=True):
        if not self.tree or not self.tree.winfo_exists():
            return
        opened = self._opened_paths() if preserve else set()
        selected = self.tree.selection() if preserve else ()
        self.loaded = set()
        self.tree.delete(*self.tree.get_children())
        self._populate('', self.folder)
        self.loaded.add(str(self.folder))
        for path in opened:
            try:
                if Path(path).is_dir() and self.tree.exists(str(path)):
                    self._expand_to(path)
                elif self.tree.exists(path):
                    self.tree.item(path, open=True)
            except OSError:
                continue
        selected = [iid for iid in selected if self.tree.exists(iid)]
        if selected:
            self.tree.selection_set(selected)

    # --- display filters --------------------------------------------------
    def ignore_patterns(self, filename='.cursorignore'):
        return read_ignore_lines(self.folder, filename)

    def set_ignore_patterns(self, patterns, filename='.cursorignore'):
        write_ignore_lines(self.folder, patterns, filename)
        self.rebuild(preserve=True)

    def ignore_selection(self):
        patterns = list(self.ignore_patterns())
        for path in self.selected_paths():
            try:
                relative = path.absolute().relative_to(self.folder.absolute()).as_posix()
            except ValueError:
                continue
            patterns.append('/' + escape_pattern(relative) + ('/' if path.is_dir() else ''))
        self.set_ignore_patterns(patterns)

    def toggle_ignored(self):
        self.show_ignored = not self.show_ignored
        self.rebuild(preserve=True)

    def edit_ignore(self):
        folder = self.folder
        dialog = tk.Toplevel(self.panel)
        dialog.title(t('ignore_title'))
        dialog.configure(bg=config.BG)
        dialog.transient(self.panel)
        tk.Label(dialog, text=t('ignore_help'), bg=config.BG, fg=config.FG,
                 justify='left', wraplength=440).pack(padx=12, pady=10)
        editor = tk.Text(dialog, width=52, height=14, bg=config.BTN, fg=config.FG,
                         insertbackground=config.FG)
        editor.pack(padx=12, pady=4)
        source = tk.StringVar(value='.cursorignore')
        chooser = ttk.Combobox(dialog, textvariable=source,
                               values=('.cursorignore', '.gitignore'), state='readonly')
        chooser.pack(padx=12, pady=4)
        def load_rules(_event=None):
            editor.delete('1.0', 'end')
            editor.insert('1.0', '\n'.join(self.ignore_patterns(source.get())))
        chooser.bind('<<ComboboxSelected>>', load_rules)
        load_rules()
        buttons = tk.Frame(dialog, bg=config.BG)
        buttons.pack(fill='x', padx=12, pady=10)
        def apply():
            if self.folder != folder:
                dialog.destroy()
                return
            try:
                self.set_ignore_patterns(editor.get('1.0', 'end-1c').splitlines(), source.get())
            except (ValueError, OSError) as error:
                messagebox.showerror(t('ignore_title'), str(error), parent=dialog)
                return
            dialog.destroy()
        self._button(buttons, t('ignore_save'), apply).pack(side='right')
        dialog.grab_set()
        editor.focus_set()

    def collapse_all(self):
        for item in self.tree.get_children():
            self.tree.item(item, open=False)

    def expand_all(self, max_depth=4):
        if not self.tree:
            return

        def walk(parent, depth):
            if depth > max_depth:
                return
            for iid in self.tree.get_children(parent):
                if iid.endswith(config.PLACEHOLDER):
                    continue
                if iid.startswith('__'):
                    self.tree.item(iid, open=True)
                    walk(iid, depth)
                elif self.path_of(iid) is not None and Path(iid).is_dir():
                    self._ensure_loaded(iid)
                    self.tree.item(iid, open=True)
                    walk(iid, depth + 1)

        walk('', 0)

    def toggle_expand(self):
        if self._expand_state:
            self.collapse_all()
            self._expand_state = False
        else:
            self.expand_all()
            self._expand_state = True
        self._sync_toggle_icon()

    def _sync_toggle_icon(self):
        if not self.toggle_btn:
            return
        self.toggle_btn.config(text='⊟' if self._expand_state else '⊞')
        label = t('tip_collapse_all') if self._expand_state else t('tip_expand_all')
        for tip in self.tips:
            if tip.widget is self.toggle_btn:
                tip.set_text(label)
                break

    def on_open(self, ev=None):
        iid = self.tree.focus()
        if iid and self.tree.exists(iid) and not iid.startswith('__') \
                and not iid.endswith(config.PLACEHOLDER) and Path(iid).is_dir():
            self._ensure_loaded(iid)



    # --- operations --------------------------------------------------------
    def new_folder(self):
        name = simpledialog.askstring(t('new_folder_title'), t('new_folder_prompt'), parent=self.panel)
        if name is None:
            return
        try:
            (self.target_dir() / safe_name(name)).mkdir()
            self.on_event('new')
            self.rebuild(preserve=True)
        except (ValueError, OSError) as exc:
            messagebox.showerror(t('err_create'), str(exc), parent=self.panel)
            self.on_event('error')

    def import_files(self):
        names = filedialog.askopenfilenames(parent=self.panel, title=t('import_title'))
        self._copy_paths([Path(n) for n in names], self.target_dir())
        self.rebuild(preserve=True)

    def on_double(self, ev):
        item = self.tree.identify_row(ev.y)
        if item:
            self.activate(item)

    def activate(self, item):
        path = self.path_of(item)
        if path is None:
            if item.startswith('__'):
                self.tree.item(item, open=not self.tree.item(item, 'open'))
            return
        if path.is_dir():
            self._ensure_loaded(item)
            self.tree.item(item, open=not self.tree.item(item, 'open'))
        elif path.exists():
            self._open_external(path)

    def _open_external(self, path):
        try:
            if sys.platform == 'win32':
                os.startfile(str(path))
            else:
                subprocess.Popen(['xdg-open', str(path)])
        except OSError as exc:
            messagebox.showerror(t('err_open'), str(exc), parent=self.panel)

    def rename(self):
        paths = self.selected_paths()
        if len(paths) != 1 or paths[0] == self.folder:
            return
        item = paths[0]
        name = simpledialog.askstring(t('rename_title'), t('rename_prompt'),
                                      initialvalue=item.name, parent=self.panel)
        if name is None:
            return
        try:
            dst = item.with_name(safe_name(name))
            if dst.exists() and dst != item:
                raise FileExistsError(t('err_exists'))
            item.rename(dst)
            self.rebuild(preserve=True)
        except (OSError, ValueError) as exc:
            messagebox.showerror(t('err_rename'), str(exc), parent=self.panel)

    def soft_delete(self):
        paths = [p for p in self.selected_paths() if p != self.folder and p.exists() and self.inside(p)]
        if not paths:
            return
        if not messagebox.askyesno(t('trash_confirm_title'), t('trash_confirm', n=len(paths)),
                                   parent=self.panel):
            return
        trash = self.folder / config.TRASH
        trash.mkdir(exist_ok=True)
        from datetime import datetime
        prefix = datetime.now().strftime('%Y%m%d_%H%M%S_')
        for p in paths:
            try:
                shutil.move(str(p), str(unique_dest(trash, prefix + p.name)))
            except OSError as exc:
                messagebox.showerror(t('err_move'), str(exc), parent=self.panel)
                self.on_event('error')
        self.on_event('delete')
        self.rebuild(preserve=True)

    # --- clipboard ---------------------------------------------------------
    def copy_selection(self):
        paths = self.selected_paths()
        if paths:
            self.clip = ('copy', paths)

    def cut_selection(self):
        paths = self.selected_paths()
        if paths:
            self.clip = ('cut', paths)

    def paste(self):
        self._paste_into(self.target_dir())

    def _paste_into(self, dest_dir):
        if not self.clip:
            return
        mode, paths = self.clip
        dest_dir = Path(dest_dir)
        try:
            for src in paths:
                if not src.exists():
                    continue
                if mode == 'cut':
                    self._move_path(src, dest_dir)
                else:
                    self._copy_path(src, dest_dir)
        finally:
            if mode == 'cut':
                self.clip = None
        self.rebuild(preserve=True)

    def copy_text(self, text):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except tk.TclError:
            pass

    def copy_path_text(self):
        paths = self.selected_paths()
        if paths:
            self.copy_text('\n'.join(str(p) for p in paths))

    def _copy_path(self, src, dest_dir):
        src, dest_dir = Path(src), Path(dest_dir)
        if src.is_dir() and (src.resolve() == dest_dir.resolve() or
                             src.resolve() in dest_dir.resolve().parents):
            return
        dest = unique_dest(dest_dir, src.name)
        if src.is_dir():
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)
        return dest

    def _move_path(self, src, dest_dir):
        src, dest_dir = Path(src), Path(dest_dir)
        if not transfer_allowed(src, dest_dir):
            return
        dest = dest_dir / src.name
        if dest.exists():
            dest = unique_dest(dest_dir, src.name)
        shutil.move(str(src), str(dest))
        return dest

    def _copy_paths(self, paths, dest_dir):
        for src in top_level_paths(paths):
            try:
                if src.exists():
                    self._copy_path(src, dest_dir)
            except OSError as exc:
                messagebox.showerror(t('err_copy'), str(exc), parent=self.panel)

    # --- hover info --------------------------------------------------------
    def _row_hover(self, ev):
        iid = self.tree.identify_row(ev.y)
        if iid == self._row_iid:
            return
        self._hide_row_tip()
        self._row_iid = iid
        if not iid:
            return
        x, y = ev.x_root + 14, ev.y_root + 18
        try:
            self._row_after = self.tree.after(
                550, lambda i=iid, px=x, py=y: self._show_row_tip(i, px, py))
        except tk.TclError:
            self._row_after = None

    def _row_tip_text(self, iid):
        path = self.path_of(iid)
        return str(path) if path is not None else ''

    def _show_row_tip(self, iid, x, y):
        if not self.tree.exists(iid):
            return
        text = self._row_tip_text(iid)
        if not text:
            return
        tip = tk.Toplevel(self.tree)
        tip.wm_overrideredirect(True)
        try:
            tip.attributes('-topmost', False)
        except tk.TclError:
            pass
        tk.Label(tip, text=text, bg=config.BTN, fg=config.FG, font=config.ui_font(9),
                 justify='left', padx=8, pady=4, wraplength=460, bd=0).pack()
        tip.geometry(f'+{x}+{y}')
        self._row_tip = tip

    def _hide_row_tip(self):
        if self._row_after:
            try:
                self.tree.after_cancel(self._row_after)
            except tk.TclError:
                pass
            self._row_after = None
        if self._row_tip:
            try:
                self._row_tip.destroy()
            except tk.TclError:
                pass
            self._row_tip = None
        self._row_iid = None

    # --- context menu ------------------------------------------------------
    def context_menu(self, ev):
        iid = self.tree.identify_row(ev.y)
        if iid and iid.endswith(config.PLACEHOLDER):
            iid = None
        if iid and iid not in self.tree.selection():
            self.tree.selection_set(iid)
        menu = tk.Menu(self.panel, tearoff=0)
        menu.add_command(label=t('menu_open_folder'), command=self.choose_folder)
        menu.add_command(label=t('menu_new_subfolder'), command=self.new_folder)
        menu.add_command(label=t('ignore_title'), command=self.edit_ignore)
        menu.add_command(label=t('ignore_hide' if self.show_ignored else 'ignore_show'),
                         command=self.toggle_ignored)
        menu.add_separator()
        menu.add_command(label=t('menu_copy'), command=self.copy_selection)
        menu.add_command(label=t('menu_cut'), command=self.cut_selection)
        state = 'normal' if self.clip else 'disabled'
        menu.add_command(label=t('menu_paste'), command=self.paste, state=state)
        path = self.path_of(iid) if iid else None
        if path:
            menu.add_separator()
            menu.add_command(label=t('menu_open'), command=lambda: self.activate(iid))
            menu.add_command(label=t('menu_copy_path'), command=self.copy_path_text)
            menu.add_command(label=t('ignore_selected'), command=self.ignore_selection)
            menu.add_command(label=t('menu_rename'), command=self.rename)
            menu.add_command(label=t('menu_trash'), command=self.soft_delete)
            menu.add_command(label=t('menu_reveal'),
                             command=lambda: self._open_external(path if path.is_dir() else path.parent))
        menu.tk_popup(ev.x_root, ev.y_root)

    # --- dragging (poll-based; DoDragDrop runs outside Tk events) ----------
    def _start_watch(self):
        self._cancel_watch()
        try:
            self._watch_after = self.tree.after(15, self._watch_external_drag)
        except tk.TclError:
            self._watch_after = None

    def _cancel_watch(self):
        self._highlight_drop(None)
        self._highlight_root(None)
        self._hide_drag_preview()
        if self._watch_after:
            try:
                self.tree.after_cancel(self._watch_after)
            except tk.TclError:
                pass
            self._watch_after = None

    def _managed_path(self, path):
        """Include every added path, even after hover switches the active tree."""
        resolved = Path(path).resolve()
        roots = getattr(self, 'roots', [str(self.folder)])
        return any(resolved == Path(r).resolve() or Path(r).resolve() in resolved.parents
                   for r in roots)

    def _root_at(self, x, y):
        for path, chip in self._root_chips.items():
            if chip.winfo_exists() and (chip.winfo_rootx() <= x < chip.winfo_rootx() + chip.winfo_width()
                    and chip.winfo_rooty() <= y < chip.winfo_rooty() + chip.winfo_height()):
                return Path(path)
        return None

    def _drop_destination(self, x, y):
        tab = self._root_at(x, y)
        if tab is not None:
            return tab
        tx, ty = x - self.tree.winfo_rootx(), y - self.tree.winfo_rooty()
        if not (0 <= tx < self.tree.winfo_width() and 0 <= ty < self.tree.winfo_height()):
            return None
        iid = self.tree.identify_row(ty)
        if not iid:
            return self.folder
        path = self.path_of(iid)
        if path is None:
            return None
        return path if path.is_dir() else path.parent

    def _highlight_root(self, path):
        key = str(path) if path is not None else None
        if key != self._drag_root:
            self._drag_root = key
            self._drag_root_since = time.monotonic()
        style_key = (key, str(self.folder))
        if style_key == self._root_style_key:
            return
        self._root_style_key = style_key
        for root, chip in self._root_chips.items():
            bg = config.DROP_BG if root == key else config.SEL if root == str(self.folder) else config.BTN
            if chip.winfo_exists():
                chip.configure(bg=bg)
                for label in chip.winfo_children():
                    label.configure(bg=bg)

    def _hide_drag_preview(self):
        if self._drag_preview is not None:
            self._drag_preview.destroy()
            self._drag_preview = None

    def _show_drag_preview(self, x, y, destination):
        from ..native.win32 import control_button_down
        if self._drag_preview is None:
            tip = self._drag_preview = tk.Toplevel(self.panel)
            tip.overrideredirect(True)
            tip.attributes('-topmost', False)
            label = tk.Label(tip, bg=config.BTN, fg=config.FG, padx=8, pady=5,
                             font=config.ui_font(9), justify='left')
            label.pack()
        label = self._drag_preview.winfo_children()[0]
        valid = destination is not None and any(transfer_allowed(p, destination) for p in self._drag_items)
        text = t('drag_copy' if control_button_down() else 'drag_move', count=len(self._drag_items))
        text += '\n' + (str(destination) if valid else t('drag_invalid'))
        if label.cget('text') != text:
            label.configure(text=text, wraplength=240)
            self._drag_preview.update_idletasks()
        w, h = self._drag_preview.winfo_reqwidth(), self._drag_preview.winfo_reqheight()
        px = min(x + 18, self.root.winfo_screenwidth() - w)
        py = min(y + 22, self.root.winfo_screenheight() - h)
        # When the right edge clamps the preview, put it left of the pointer
        # so it never covers the destination under the mouse.
        if px <= x < px + w:
            px = x - w - 18
        self._drag_preview.geometry(f'+{max(0, px)}+{max(0, py)}')

    def cancel_drag(self, _event=None):
        if not self._drag_active:
            return
        self._drag_active = False
        self._drag_items = self._drag_text = None
        self._cancel_watch()
        return 'break'

    def _highlight_drop(self, iid):
        if self._drag_hover == iid:
            return
        if self._drag_hover and self.tree.exists(self._drag_hover):
            tags = tuple(t for t in self.tree.item(self._drag_hover, 'tags') if t != 'drop_target')
            self.tree.item(self._drag_hover, tags=tags)
        self._drag_hover = iid
        self._drag_hover_since = time.monotonic()
        if iid and self.tree.exists(iid):
            self.tree.item(iid, tags=tuple(self.tree.item(iid, 'tags')) + ('drop_target',))

    def drag_start(self, ev):
        self._press_xy = (ev.x_root, ev.y_root)
        self._drag_moved = False
        iid = self.tree.identify_row(ev.y)
        if iid and iid.endswith(config.PLACEHOLDER):
            iid = None
        if iid and iid not in self.tree.selection():
            self.tree.selection_set(iid)
        self._press_iid = iid
        self._drag_items = top_level_paths(self.selected_paths()) if iid else None
        self._drag_text = None
        self._drag_event = None
        self._drag_active = bool(self._drag_items or self._drag_text)
        if self._drag_active:
            self._start_watch()

    def _watch_external_drag(self):
        """Poll the cursor; start a native drag once it leaves the panel.

        DoDragDrop is blocking and must not be called from inside a Tk mouse
        event (Tk holds the pointer grab then, which deadlocks the drag loop),
        so it is started here, from an ``after`` callback.
        """
        self._watch_after = None
        if not self._drag_active:
            return
        if not left_button_down():
            self._cancel_watch()
            return
        x, y = get_cursor_pos()
        if self._press_xy and max(abs(x - self._press_xy[0]), abs(y - self._press_xy[1])) >= 6:
            self._drag_moved = True
        if not self._drag_moved:
            self._watch_after = self.tree.after(15, self._watch_external_drag)
            return
        px, py = self.panel.winfo_rootx(), self.panel.winfo_rooty()
        pw, ph = self.panel.winfo_width(), self.panel.winfo_height()
        if not (px <= x <= px + pw and py <= y <= py + ph):
            items, text = self._drag_items, self._drag_text
            self._cancel_watch()
            self._drag_active = False
            self._drag_items = None
            self._drag_text = None
            for widget in (self.tree, self.panel):
                try:
                    widget.grab_release()
                except tk.TclError:
                    pass
            if self._drag_event:
                self.on_event(self._drag_event)
                self._drag_event = None
            if items:
                start_ole_drag(paths=[str(p) for p in items])
            elif text:
                start_ole_drag(text=text)
            self.rebuild(preserve=True)
            return
        if self._drag_items and self._drag_event != 'skill_drag':
            self._hide_row_tip()
            tab = self._root_at(x, y)
            self._highlight_root(tab)
            if tab is not None and str(tab) != str(self.folder) and time.monotonic() - self._drag_root_since >= 0.45:
                self._highlight_drop(None)
                self.set_folder(tab)
                self.panel.update_idletasks()
                self._highlight_root(tab)
            self._show_drag_preview(x, y, self._drop_destination(x, y))
            tx, ty = x - self.tree.winfo_rootx(), y - self.tree.winfo_rooty()
            height = self.tree.winfo_height()
            if 0 <= tx < self.tree.winfo_width() and 0 <= ty < height:
                now = time.monotonic()
                if now - self._drag_scroll_at > 0.12:
                    if ty < 24:
                        self.tree.yview_scroll(-1, 'units')
                    elif ty > height - 24:
                        self.tree.yview_scroll(1, 'units')
                    self._drag_scroll_at = now
                iid = self.tree.identify_row(ty)
                dst = self.path_of(iid)
                valid = dst is not None and dst.is_dir() and self.inside(dst) and any(
                    transfer_allowed(p, dst) for p in self._drag_items)
                self._highlight_drop(iid if valid else None)
                if valid and now - self._drag_hover_since >= 0.65:
                    self._ensure_loaded(iid)
                    self.tree.item(iid, open=True)
            else:
                self._highlight_drop(None)
        self._watch_after = self.tree.after(15, self._watch_external_drag)

    def drag_end(self, ev):
        moved = self._drag_moved or (self._press_xy is not None and max(
            abs(ev.x_root - self._press_xy[0]), abs(ev.y_root - self._press_xy[1])) >= 6)
        self._cancel_watch()
        items = self._drag_items
        started = not self._drag_active      # the watchdog handed off to OLE
        self._drag_items = None
        self._drag_text = None
        self._drag_active = False
        iid = getattr(self, '_press_iid', None)
        self._press_iid = None
        if started:
            return
        if not items:
            return
        if not moved:
            return
        dst = self._drop_destination(ev.x_root, ev.y_root)
        if dst is None or not dst.is_dir() or not self._managed_path(dst):
            return
        copy = bool(ev.state & 0x0004)
        transferred = []
        for src in items:
            if not src.exists() or not self._managed_path(src):
                continue
            if not transfer_allowed(src, dst):
                continue
            try:
                if copy:
                    transferred.append(self._copy_path(src, dst))
                else:
                    transferred.append(self._move_path(src, dst))
            except OSError as exc:
                messagebox.showerror(t('err_operation'), str(exc), parent=self.panel)
                self.on_event('error')
        if not transferred:
            return
        self.on_event('file_copy' if copy else 'file_move')
        if self._root_at(ev.x_root, ev.y_root) is not None and dst != self.folder:
            self.set_folder(dst)
        self.rebuild(preserve=True)
        for path in transferred:
            if path is not None and self.inside(path):
                self._expand_to(str(path))
        self.tree.selection_set([str(path) for path in transferred if path is not None and self.tree.exists(str(path))])

    def _on_panel_drop(self, paths, copy, point):
        dst = self._drop_destination(*point)
        if dst is None or not self._managed_path(dst):
            return
        for src in top_level_paths(paths):
            if not src.exists():
                continue
            internal = self._managed_path(src)
            if not transfer_allowed(src, dst):
                continue
            try:
                if internal and not copy:
                    self._move_path(src, dst)
                else:
                    self._copy_path(src, dst)
            except OSError as exc:
                messagebox.showerror(t('err_operation'), str(exc), parent=self.panel)
        self.rebuild(preserve=True)
