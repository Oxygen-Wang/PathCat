"""Prepare small transparent sprites from the original cat artwork (Pillow)."""
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / 'resources/cats/calico'
    destination = ROOT / 'quietpet/assets/cat/calico'
    destination.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / 'quietpet/assets/cat/manifest.json').read_text(encoding='utf-8'))
    for name, entry in manifest['states'].items():
        image_path = source / f'{name}.png'
        entry['frames'] = []
        entry.pop('optional_frames', None)
        if not image_path.is_file():
            continue
        with Image.open(image_path) as original:
            image = original.convert('RGBA')
            bounds = image.getchannel('A').getbbox()
            if bounds:
                image = image.crop(bounds)
            image.thumbnail((256, 256), Image.Resampling.LANCZOS)
            sprite = Image.new('RGBA', (256, 256))
            sprite.alpha_composite(image, ((256 - image.width) // 2, 256 - image.height))
            filename = f'cat_{name}_0.png'
            sprite.save(destination / filename)
        entry['frames'] = [filename]
    (destination / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
