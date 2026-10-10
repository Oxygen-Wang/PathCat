"""Read-only discovery of locally installed skill documents."""
import json
import os
from pathlib import Path
from .config import GLOBAL_SKILL_SOURCES, OC_CONFIG, PROJECT_SKILL_SUBDIRS
from .util import strip_jsonc

def _frontmatter(md_path):
    name = desc = ''
    try:
        lines = Path(md_path).read_text(encoding='utf-8', errors='ignore').splitlines()
    except OSError:
        return name, desc
    if not lines or lines[0].strip() != '---':
        return name, desc
    i = 1
    while i < len(lines):
        line = lines[i]
        if line.strip() == '---':
            break
        if ':' in line and not line.startswith((' ', '\t')):
            key, _, value = line.partition(':')
            key = key.strip().lower()
            value = value.strip()
            if value in ('>', '>-', '>+', '|', '|-', '|+'):
                block = []
                j = i + 1
                while j < len(lines) and lines[j].strip() and lines[j][:1] in (' ', '\t'):
                    block.append(lines[j].strip())
                    j += 1
                value = ' '.join(block)
                i = j
            else:
                value = value.strip('"').strip("'")
                i += 1
            if key == 'name':
                name = value
            elif key == 'description':
                desc = value
            continue
        i += 1
    return name, desc


def _iter_skills_in(source):
    """Yield (skill_id, markdown_path) for one skills source directory."""
    source = Path(source)
    if not source.is_dir():
        return
    seen = set()
    try:
        entries = sorted(source.iterdir(), key=lambda p: p.name.casefold())
    except OSError:
        return
    for entry in entries:
        if entry.is_file() and entry.suffix.lower() == '.md':
            if entry.name.lower() != 'skill.md':
                seen.add(entry.resolve())
                yield entry.stem, entry
    try:
        for md in sorted(source.rglob('SKILL.md')):
            if md.is_file() and md.resolve() not in seen:
                yield md.parent.name, md
    except OSError:
        return


def _project_skill_sources(project_dir):
    if not project_dir:
        return []
    try:
        start = Path(project_dir).resolve()
    except OSError:
        return []
    ancestors = [start] + list(start.parents)
    ancestors.reverse()  # farthest ancestor first, project last (higher precedence)
    dirs = []
    for base in ancestors:
        for sub in PROJECT_SKILL_SUBDIRS:
            dirs.append(base / sub)
    return dirs


def _config_skill_sources(config_paths, base):
    dirs = []
    for cfg in config_paths:
        cfg = Path(cfg)
        if not cfg.exists():
            continue
        try:
            data = json.loads(strip_jsonc(cfg.read_text(encoding='utf-8')))
        except Exception:
            continue
        for entry in data.get('skills') or []:
            if not isinstance(entry, str) or entry.startswith(('http://', 'https://')):
                continue
            expanded = Path(os.path.expanduser(entry))
            if not expanded.is_absolute():
                expanded = Path(base) / expanded
            dirs.append(expanded)
    return dirs


def read_skill_text(md_path, limit=800):
    """Return a skill's body (frontmatter stripped), truncated for previews."""
    try:
        text = Path(md_path).read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return ''
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end != -1:
            text = text[end + 4:]
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + '…'


def list_open_skills(project_dir=None, extra_roots=None, config_paths=None):
    """Discover skills the way opencode V2 does.

    Returns a list of dicts: {id, name, description, path, source}.
    Later sources override earlier ones by id, per opencode precedence.
    """
    base = Path(project_dir) if project_dir else Path.cwd()
    config_paths = list(config_paths or [OC_CONFIG])
    sources = list(GLOBAL_SKILL_SOURCES)
    sources += _project_skill_sources(project_dir)
    sources += list(extra_roots or [])
    sources += _config_skill_sources(config_paths, base)

    found = {}
    for src in sources:
        for skill_id, md in _iter_skills_in(src):
            name, desc = _frontmatter(md)
            found[skill_id] = {'id': skill_id, 'name': name or skill_id,
                               'description': desc, 'path': md, 'source': str(Path(src))}
    return sorted(found.values(), key=lambda s: s['id'].casefold())
