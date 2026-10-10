"""Generate this machine's plugin configuration and a ZIP for local import."""
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/quietpet-codex'


def main():
    config = {'mcpServers': {'quietpet': {
        'type': 'stdio', 'command': sys.executable,
        'args': [str(ROOT / 'codex_mcp_entry.py')]}}}
    (PLUGIN / '.mcp.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    output = ROOT / 'dist/QuietPetCodexPlugin.zip'
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in PLUGIN.rglob('*'):
            if path.is_file():
                archive.write(path, path.relative_to(PLUGIN).as_posix())
    print(output)


if __name__ == '__main__':
    main()
