"""Build the README's illustrated walkthrough (Pillow is a docs-only dependency)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'media'
OUT.mkdir(parents=True, exist_ok=True)
FONT = Path('C:/Windows/Fonts/msyh.ttc')


def font(size):
    return ImageFont.truetype(str(FONT), size)


def folder(draw, x, y, name):
    draw.rounded_rectangle((x, y, x + 50, y + 18), 6, fill='#e4b962')
    draw.rounded_rectangle((x, y + 10, x + 100, y + 72), 10, fill='#f3ce83')
    draw.text((x, y + 82), name, font=font(18), fill='#55534c')


frames = []
steps = [
    ('01  把文件夹交给小猫', '拖入文件夹，打开你的路径。', 'file_in'),
    ('02  点一下，文件就在手边', '点击小猫或按 Ctrl+B，展开文件侧栏。', 'panel_open'),
    ('03  拖过去，整理好', '跨路径拖动移动；按住 Ctrl 拖动复制。', 'file_move'),
    ('04  收起来，继续专注', '再点一下小猫，收起侧栏。', 'happy'),
]
for step, (title, subtitle, state) in enumerate(steps):
    for tick in range(18):
        im = Image.new('RGB', (960, 480), '#faf6ee')
        d = ImageDraw.Draw(im)
        d.text((42, 28), title, font=font(30), fill='#343f38')
        d.text((42, 76), subtitle, font=font(20), fill='#66685f')
        d.rounded_rectangle((42, 132, 918, 396), 20, fill='#ede9df')
        d.text((68, 155), '我的桌面', font=font(18), fill='#8b887e')
        folder(d, 95, 218, '项目文件夹')
        if step in (1, 2):
            d.rounded_rectangle((626, 146, 902, 382), 14, fill='#fffdf8')
            d.rounded_rectangle((642, 162, 753, 198), 8, fill='#dce7da')
            d.text((658, 168), '项目 A', font=font(18), fill='#465746')
            d.text((779, 168), '项目 B', font=font(18), fill='#66685f')
            for row, label in enumerate(['📁  素材', '    notes.md', '    photo.png', '📁  文档']):
                d.text((651, 216 + row * 34), label, font=font(18), fill='#55534c')
        cat = Image.open(ROOT / f'quietpet/assets/cat/{state}/cat_{state}_0.png').convert('RGBA')
        im.paste(cat, (535 if step in (1, 2) else 800, 270), cat)
        progress = tick / 17
        if step == 0:
            x = int(225 + 535 * progress)
            folder(d, x, 221, '')
        if step == 2:
            x = int(675 + 134 * progress)
            y = int(284 - 90 * progress)
            d.rounded_rectangle((x, y, x + 76, y + 28), 5, fill='#dce7da')
            d.text((x + 5, y + 3), 'notes.md', font=font(13), fill='#465746')
        for dot in range(4):
            x = 432 + dot * 28
            d.ellipse((x, 421, x + 10, 431), fill='#76947b' if dot == step else '#d7d9cc')
        d.text((42, 443), 'PathCat · 操作示意动画（非实机录屏）', font=font(14), fill='#8b887e')
        frames.append(im)
frames[0].save(OUT / 'pathcat-walkthrough.gif', save_all=True,
               append_images=frames[1:], duration=110, loop=0, optimize=True)
print(OUT / 'pathcat-walkthrough.gif')
