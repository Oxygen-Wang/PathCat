# -*- coding: utf-8 -*-
"""The file explorer sidebar: lazy tree, skill chips, clipboard, drag/copy/move."""
import os
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, simpledialog, messagebox

from ..core import config
from ..core.i18n import t
from .icons import load_icons
from ..opencode.status import list_open_skills, read_mcp_servers, read_skill_text
from ..core.util import safe_name, unique_dest
from .widgets import ToolTip
from ..native.win32 import (force_top, get_cursor_pos, install_drop_targets,
                            left_button_down, register_drop_target, start_ole_drag)

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
        self.refs = {}
        self.usage = dict(settings.get('skill_usage') or {})
        self.labels = dict(settings.get('skill_labels') or {})
        self._body_cache = {}
        self.loaded = set()
        self.clip = None

        self.skills_area = None
        self.skills_header = None
        self._skills = []
        self._skills_width = 0
        self._skills_after = None
        self._skills_expanded = bool(settings.get('skills_expanded', False))

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
        w.attributes('-topmost', True)
        w.protocol('WM_DELETE_WINDOW', self.hide)
        self.icons = load_icons(master=self.root, size=16, color='#cfd3da')
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
                                    bg=config.BTN, fg='#e2e2e4', activebackground=config.BTN_HOVER,
                                    activeforeground='white', relief='flat', borderwidth=0,
                                    padx=8, pady=3, cursor='hand2', font=('Segoe UI', 11),
                                    highlightthickness=0)
        self.toggle_btn.pack(side='left', padx=2)
        self.tips.append(ToolTip(self.toggle_btn, t('tip_expand_all')))

        style = ttk.Style(w)
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure('Quiet.Treeview', background=config.BG, fieldbackground=config.BG,
                        foreground=config.FG, borderwidth=0, rowheight=27, font=('Segoe UI', 10))
        style.map('Quiet.Treeview', background=[('selected', config.SEL)],
                  foreground=[('selected', '#ffffff')])

        body = tk.Frame(self.inner, bg=config.BG)
        tree = ttk.Treeview(body, show='tree', style='Quiet.Treeview', selectmode='extended')
        self.tree = tree
        bar = ttk.Scrollbar(body, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=bar.set)
        tree.pack(side='left', fill='both', expand=True)
        bar.pack(side='right', fill='y')
        tree.bind('<Double-1>', self.on_double)
        tree.bind('<Button-3>', self.context_menu)
        tree.bind('<ButtonPress-1>', self.drag_start)
        tree.bind('<ButtonRelease-1>', self.drag_end)
        tree.bind('<<TreeviewOpen>>', self.on_open)
        tree.bind('<Control-c>', lambda e: self.copy_selection())
        tree.bind('<Control-x>', lambda e: self.cut_selection())
        tree.bind('<Control-v>', lambda e: self.paste())
        tree.bind('<F2>', lambda e: self.rename())
        tree.bind('<Delete>', lambda e: self.soft_delete())
        tree.bind('<Motion>', self._row_hover, add='+')
        tree.bind('<Leave>', lambda e: self._hide_row_tip(), add='+')

        footer = tk.Label(self.inner, text=t('footer'),
                          bg=config.BG, fg=config.MUTED, font=('Segoe UI', 9), anchor='w')
        footer.pack(side='bottom', fill='x', padx=14, pady=10)

        # Skills dock at the bottom and fill from bottom to top.
        self.skills_area = tk.Frame(self.inner, bg=config.BG)
        self.skills_area.pack(side='bottom', fill='x', padx=10, pady=(0, 2))
        self.skills_area.bind('<Configure>', self._on_skills_configure)
        skills_head = tk.Frame(self.inner, bg=config.BG)
        skills_head.pack(side='bottom', fill='x', padx=12, pady=(0, 2))
        self.skills_header = tk.Label(skills_head, text='', bg=config.BG, fg=config.MUTED,
                                      font=('Segoe UI', 8, 'bold'), anchor='w', cursor='hand2')
        self.skills_header.pack(side='left')
        self.skills_header.bind('<Button-1>', lambda e: self.toggle_skills())

        body.pack(fill='both', expand=True, padx=(8, 6))

        self.update_labels()
        self.rebuild(preserve=False)
        if not register_drop_target(w.winfo_id(), self._on_panel_drop) and \
                not register_drop_target(tree.winfo_id(), self._on_panel_drop):
            install_drop_targets(w, self.on_os_drop, self.drop_targets)
        force_top(w.winfo_id())
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
            self.panel.title(f'QuietPet · {name}')
        if self.roots_bar is not None and self.roots_bar.winfo_exists():
            self._build_roots_bar()

    def _build_roots_bar(self):
        for child in self.roots_bar.winfo_children():
            child.destroy()
        active = str(self.folder)
        for root in self.roots:
            selected = str(Path(root)) == active
            bg = config.SEL if selected else config.BTN
            chip = tk.Frame(self.roots_bar, bg=bg)
            name = Path(root).name or str(root)
            label = tk.Label(chip, text=name, bg=bg, fg='#e8eaed', padx=7, pady=2,
                             font=('Segoe UI', 9), cursor='hand2')
            label.pack(side='left')
            close = tk.Label(chip, text='×', bg=bg, fg=config.MUTED, padx=2, pady=2,
                             font=('Segoe UI', 9), cursor='hand2')
            close.pack(side='left')
            label.bind('<Button-1>', lambda e, r=root: self.set_folder(r))
            close.bind('<Button-1>', lambda e, r=root: self.remove_root(r))
            chip.pack(side='left', padx=2)
            self.tips.append(ToolTip(chip, str(root)))
        add = tk.Label(self.roots_bar, text='＋', bg=config.BTN, fg='#e8eaed', padx=7, pady=2,
                       font=('Segoe UI', 10, 'bold'), cursor='hand2')
        add.pack(side='left', padx=2)
        add.bind('<Button-1>', lambda e: self.add_root())
        self.tips.append(ToolTip(add, t('add_path')))

    def _button(self, parent, label, command, small=False, tip=None):
        btn = tk.Button(parent, text=label, command=command, bg=config.BTN, fg='#e2e2e4',
                        activebackground=config.BTN_HOVER, activeforeground='white', relief='flat',
                        padx=6 if small else 8, pady=3 if small else 5, cursor='hand2',
                        borderwidth=0, font=('Segoe UI', 9), highlightthickness=0)
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

    def mcp_config_paths(self):
        paths = [config.OC_CONFIG]
        try:
            start = self.folder.resolve()
            for base in [start] + list(start.parents):
                for name in ('opencode.json', 'opencode.jsonc',
                             '.opencode/opencode.json', '.opencode/opencode.jsonc'):
                    p = base / name
                    if p.exists() and p not in paths:
                        paths.append(p)
        except OSError:
            pass
        return paths

    def on_os_drop(self, paths):
        self._copy_paths([Path(p) for p in paths], self.target_dir())
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
        if not iid or iid.endswith(config.PLACEHOLDER) or iid.startswith('__') \
                or iid.startswith(config.MCP_PREFIX):
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
            entries = [p for p in directory.iterdir() if p.name != config.TRASH]
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

    def _populate_sections(self):
        config_paths = self.mcp_config_paths()
        has_icons = bool(self.icons)
        servers = read_mcp_servers(config_paths)
        self._insert('', config.SEC_MCP,
                     ('🔌 ' if not has_icons else '') + f'MCP ({len(servers)})', 'mcp')
        for server in servers:
            iid = config.MCP_PREFIX + server['name']
            label = f"{server['name']}  ·  {server['type']}"
            if server['detail']:
                label += f"  ·  {self._short(server['detail'])}"
            if server['disabled']:
                label += f"  ({t('disabled')})"
            self._insert(config.SEC_MCP, iid, ('🔌 ' if not has_icons else '') + label, 'mcp')
            self.refs[iid] = {'kind': 'mcp', 'text': server['name'], 'name': server['name'],
                              'path': None, 'type': server['type'], 'detail': server['detail']}
        if not servers:
            self._insert(config.SEC_MCP, config.MCP_PREFIX + '::empty', t('mcp_unconfigured'))
        self.loaded.add(config.SEC_MCP)

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
        self.refs = {}
        self.tree.delete(*self.tree.get_children())
        self._populate('', self.folder)
        self.loaded.add(str(self.folder))
        self._populate_sections()
        for path in opened:
            try:
                if Path(path).is_dir() and self.tree.exists(str(path)):
                    self._expand_to(path)
                elif self.tree.exists(path):
                    self.tree.item(path, open=True)
            except OSError:
                continue
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected)
        self._build_skills()

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

    # --- skill chips (bottom, most-used first) ----------------------------
    def _skill_detail(self, skill):
        used = self.usage.get(skill['id'], 0)
        head = f"{skill['id']}  ({skill['name']})" + (f"  ·  已用 {used} 次" if used else '')
        body = ''
        if skill.get('path'):
            if skill['id'] not in self._body_cache:
                self._body_cache[skill['id']] = read_skill_text(skill['path'], limit=500)
            body = self._body_cache[skill['id']]
        parts = [head, skill.get('description') or '', body, str(skill.get('path') or '')]
        return '\n'.join(p for p in parts if p)

    def _on_skills_configure(self, ev):
        if abs(ev.width - self._skills_width) > 6:
            self._skills_width = ev.width
            if self._skills_after:
                try:
                    self.skills_area.after_cancel(self._skills_after)
                except tk.TclError:
                    pass
            self._skills_after = self.skills_area.after(60, self._build_skills)

    def _build_skills(self):
        if not self.skills_area or not self.skills_area.winfo_exists():
            return
        for child in self.skills_area.winfo_children():
            child.destroy()
        skills = list_open_skills(project_dir=self.folder, config_paths=self.mcp_config_paths())
        skills.sort(key=lambda s: (-self.usage.get(s['id'], 0), s['id'].casefold()))
        self._skills = skills
        if self.skills_header:
            arrow = '▾' if self._skills_expanded else '▸'
            self.skills_header.config(text=f"{arrow} {t('skills')} ({len(skills)})")
        area_w = self.skills_area.winfo_width()
        if area_w <= 1:
            area_w = 320
        row = None
        x = 0
        for index, skill in enumerate(skills):
            text = self.labels.get(skill['id'], skill['name'])
            width = max(46, len(text) * 8 + 18)
            if row is None:
                row = tk.Frame(self.skills_area, bg=config.BG)
                row.pack(side='bottom', fill='x', anchor='w')
                x = 0
            elif self._skills_expanded and x + width > area_w:
                row = tk.Frame(self.skills_area, bg=config.BG)
                row.pack(side='bottom', fill='x', anchor='w')
                x = 0
            elif not self._skills_expanded and x + width > area_w:
                break
            top = index < 5
            chip = tk.Label(row, text=text, bg=config.SEL if top else config.BTN,
                            fg='#ffffff' if top else '#e6e8eb', padx=8, pady=3,
                            font=('Segoe UI', 9), cursor='hand2')
            chip.pack(side='left', padx=2, pady=2)
            self._bind_chip(chip, skill)
            x += width

    def toggle_skills(self):
        self._skills_expanded = not self._skills_expanded
        self.settings['skills_expanded'] = self._skills_expanded
        self.save()
        self._build_skills()

    def _bind_chip(self, chip, skill):
        chip.bind('<ButtonPress-1>', lambda e, s=skill: self._chip_press(e, s))
        chip.bind('<B1-Motion>', self._chip_motion)
        chip.bind('<ButtonRelease-1>', self._chip_release)
        chip.bind('<Button-3>', lambda e, s=skill: self._chip_menu(e, s))
        self.tips.append(ToolTip(chip, self._skill_detail(skill)))

    def _chip_press(self, ev, skill):
        self._chip_ref = skill
        self._drag_items = [Path(skill['path'])] if skill.get('path') else None
        self._drag_text = None
        self._drag_active = bool(self._drag_items)
        if self._drag_active:
            self._start_watch()

    def _chip_motion(self, ev):
        pass

    def _chip_release(self, ev):
        skill = self._chip_ref
        started = not self._drag_active
        self._chip_ref = None
        self._cancel_watch()
        self._drag_items = None
        self._drag_text = None
        self._drag_active = False
        if skill and not started:
            self.copy_text('@' + skill['id'])
            self._bump_skill(skill['id'])
            self._build_skills()

    def _chip_menu(self, ev, skill):
        menu = tk.Menu(self.panel, tearoff=0)
        menu.add_command(label=t('menu_copy_skill_ref', ref='@' + skill['id']),
                         command=lambda s=skill: (self.copy_text('@' + s['id']),
                                                  self._bump_skill(s['id']),
                                                  self._build_skills()))
        menu.add_command(label=t('menu_open_skill'),
                         command=lambda s=skill: self._open_external(s['path']))
        menu.add_command(label=t('menu_copy_skill_id', id=skill['id']),
                         command=lambda s=skill: self.copy_text(s['id']))
        menu.add_separator()
        menu.add_command(label=t('skill_set_name'),
                         command=lambda s=skill: self._set_skill_label(s))
        menu.tk_popup(ev.x_root, ev.y_root)

    def _set_skill_label(self, skill):
        current = self.labels.get(skill['id'], skill['name'])
        name = simpledialog.askstring(t('skill_set_name'), t('skill_name_prompt'),
                                      initialvalue=current, parent=self.panel)
        if name is None:
            return
        name = name.strip()
        if name:
            self.labels[skill['id']] = name
        else:
            self.labels.pop(skill['id'], None)
        self.settings['skill_labels'] = self.labels
        self.save()
        self._build_skills()

    def _bump_skill(self, skill_id):
        if not skill_id:
            return
        self.usage[skill_id] = self.usage.get(skill_id, 0) + 1
        self.settings['skill_usage'] = self.usage
        self.save()

    # --- operations --------------------------------------------------------
    def new_folder(self):
        name = simpledialog.askstring(t('new_folder_title'), t('new_folder_prompt'), parent=self.panel)
        if name is None:
            return
        try:
            (self.target_dir() / safe_name(name)).mkdir()
            self.rebuild(preserve=True)
        except (ValueError, OSError) as exc:
            messagebox.showerror(t('err_create'), str(exc), parent=self.panel)

    def import_files(self):
        names = filedialog.askopenfilenames(parent=self.panel, title=t('import_title'))
        self._copy_paths([Path(n) for n in names], self.target_dir())
        self.rebuild(preserve=True)

    def on_double(self, ev):
        item = self.tree.identify_row(ev.y)
        if item:
            self.activate(item)

    def activate(self, item):
        ref = self.refs.get(item)
        if ref:
            if ref['kind'] == 'skill' and ref.get('path'):
                self._open_external(ref['path'])
            else:
                self.copy_text(ref['text'])
            return
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
        dest = unique_dest(dest_dir, src.name)
        if src.is_dir():
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)

    def _move_path(self, src, dest_dir):
        src, dest_dir = Path(src), Path(dest_dir)
        if src.resolve().parent == dest_dir.resolve():
            return
        dest = dest_dir / src.name
        if dest.exists():
            dest = unique_dest(dest_dir, src.name)
        shutil.move(str(src), str(dest))

    def _copy_paths(self, paths, dest_dir):
        for src in paths:
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
        ref = self.refs.get(iid)
        if ref:
            if ref['kind'] == 'skill':
                used = self.usage.get(ref['id'], 0)
                head = f"{ref['id']}  ({ref['name']})" + (f"  ·  已用 {used} 次" if used else '')
                body = ''
                if ref.get('path'):
                    if ref['id'] not in self._body_cache:
                        self._body_cache[ref['id']] = read_skill_text(ref['path'], limit=500)
                    body = self._body_cache[ref['id']]
                parts = [head, ref.get('description') or '', body, str(ref.get('path') or '')]
            else:
                parts = [ref.get('name', ''), ref.get('type') or '', ref.get('detail') or '']
            return '\n'.join(p for p in parts if p)
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
            tip.attributes('-topmost', True)
        except tk.TclError:
            pass
        tk.Label(tip, text=text, bg='#2b2d31', fg='#e6e8eb', font=('Segoe UI', 9),
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
        menu.add_separator()
        menu.add_command(label=t('menu_copy'), command=self.copy_selection)
        menu.add_command(label=t('menu_cut'), command=self.cut_selection)
        state = 'normal' if self.clip else 'disabled'
        menu.add_command(label=t('menu_paste'), command=self.paste, state=state)
        path = self.path_of(iid) if iid else None
        ref = self.refs.get(iid) if iid else None
        if ref:
            menu.add_separator()
            if ref['kind'] == 'skill':
                menu.add_command(label=t('menu_copy_skill_ref', ref=ref['text']),
                                 command=lambda r=ref: (self._bump_skill(r['id']),
                                                        self.copy_text(r['text'])))
                menu.add_command(label=t('menu_open_skill'),
                                 command=lambda: self._open_external(ref['path']))
            else:
                menu.add_command(label=t('menu_copy_mcp_name', name=ref['name']),
                                 command=lambda: self.copy_text(ref['text']))
                menu.add_command(label=t('menu_copy_mcp_prefix', name=ref['name']),
                                 command=lambda: self.copy_text(f"tools.{ref['name']}."))
        if path:
            menu.add_separator()
            menu.add_command(label=t('menu_open'), command=lambda: self.activate(iid))
            menu.add_command(label=t('menu_copy_path'), command=self.copy_path_text)
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
        if self._watch_after:
            try:
                self.tree.after_cancel(self._watch_after)
            except tk.TclError:
                pass
            self._watch_after = None

    def drag_start(self, ev):
        iid = self.tree.identify_row(ev.y)
        if iid and iid.endswith(config.PLACEHOLDER):
            iid = None
        if iid and iid not in self.tree.selection():
            self.tree.selection_set(iid)
        self._press_iid = iid
        self._drag_items = self.selected_paths() or None
        self._drag_text = None
        if not self._drag_items:
            ref = self.refs.get(iid)
            if ref and ref.get('text'):
                self._drag_text = ref['text']
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
            self._drag_active = False
            return
        x, y = get_cursor_pos()
        px, py = self.panel.winfo_rootx(), self.panel.winfo_rooty()
        pw, ph = self.panel.winfo_width(), self.panel.winfo_height()
        if not (px <= x <= px + pw and py <= y <= py + ph):
            items, text = self._drag_items, self._drag_text
            self._drag_active = False
            self._drag_items = None
            self._drag_text = None
            for widget in (self.tree, self.panel):
                try:
                    widget.grab_release()
                except tk.TclError:
                    pass
            if items:
                start_ole_drag(paths=[str(p) for p in items])
            elif text:
                start_ole_drag(text=text)
            return
        self._watch_after = self.tree.after(15, self._watch_external_drag)

    def drag_end(self, ev):
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
            ref = self.refs.get(iid)
            if ref and ref['kind'] == 'mcp':
                self.copy_text(ref['text'])
            return
        target = self.tree.identify_row(ev.y)
        dst = self.path_of(target)
        if dst is None or not dst.is_dir() or not self.inside(dst):
            return
        copy = bool(ev.state & 0x0004)
        for src in items:
            if not src.exists() or not self.inside(src):
                continue
            if src == dst or src in dst.parents or src.parent == dst:
                continue
            try:
                if copy:
                    self._copy_path(src, dst)
                else:
                    self._move_path(src, dst)
            except OSError as exc:
                messagebox.showerror(t('err_operation'), str(exc), parent=self.panel)
        self.rebuild(preserve=True)

    def _on_panel_drop(self, paths, copy, point):
        try:
            y = point[1] - self.tree.winfo_rooty()
        except tk.TclError:
            y = -1
        dst = self.path_of(self.tree.identify_row(max(0, y)))
        if dst is None or not dst.is_dir():
            dst = self.folder
        for raw in paths:
            src = Path(raw)
            if not src.exists():
                continue
            internal = self.inside(src)
            if internal and (src == dst or dst in src.parents or (src.is_dir() and src.parent == dst)):
                continue
            try:
                if internal and not copy:
                    self._move_path(src, dst)
                else:
                    self._copy_path(src, dst)
            except OSError as exc:
                messagebox.showerror(t('err_operation'), str(exc), parent=self.panel)
        self.rebuild(preserve=True)
