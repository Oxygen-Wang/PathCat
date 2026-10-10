# README 展示素材

- `pathcat-cover.png`：使用内置 imagegen 生成的宣传插画，不是应用截图。
- `pathcat-file-drag-v1.png`：参考毛绒小猫生成的双手举高拿文件夹旧版原图，仅保留作历史参考，应用不再使用其缩略图。
- `pathcat-walkthrough.gif`：约 8 秒的循环操作示意动画，不是实机录屏；猫咪使用项目已有状态素材。
- 重建动画：安装文档工具依赖 Pillow 后运行 `python tools/build_readme_animation.py`。应用运行不依赖 Pillow。

## 毛绒伙伴动作提示词

完整提示词见 [PET_IMAGE_PROMPTS.md](../PET_IMAGE_PROMPTS.md)，包含 6 种猫咪、1 种袋鼠及新增的 `file_drag` 双手空举高动作。角色动作与文件、文件夹等图标分开制作，当前提示词不生成手持物品；图标后续单独制作。

`pathcat-file-drag-v1.png` 与 `cat_file_drag_0.png` 是已生成的举文件夹旧素材，应用已停止使用该拖拽图。新动作通过 manifest 中 `file_drag` 状态的 `optional_frames` 加载 `file_drag/cat_file_drag_empty_0.png`；图片缺失时使用默认 idle 小猫，默认图也缺失时使用程序绘制的小猫。该新图不是必需素材，文件和文件夹图标后续作为独立图层接入。

## 封面生成提示词

```text
Use case: ads-marketing. Asset type: wide GitHub README cover illustration for PathCat, a Windows desktop file sidebar with a cat mascot. Create a charming polished kawaii editorial illustration, landscape 1536x1024. Warm cream background, soft sage and peach accents. Main character a small charcoal gray kitten with peach inner ears, round dark eyes, tiny pink nose, cream muzzle and chest, friendly proportions. Kitten sits beside neatly stacked golden file folders and a stylized desktop sidebar with folder shapes, playful dotted path connecting folders. Cozy helpful mood, clean spacious composition, subtle paper texture, rounded forms. Text verbatim: "PathCat" in large clear elegant rounded typography and small "Keep your files within reach." beneath it. No other text, no watermark. This is a promotional illustration, not an actual software screenshot.
```
