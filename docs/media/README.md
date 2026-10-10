# README 展示素材

- `pathcat-cover.png`：使用内置 imagegen 生成的宣传插画，不是应用截图。
- `pathcat-walkthrough.gif`：约 8 秒的循环操作示意动画，不是实机录屏；猫咪使用项目已有状态素材。
- 重建动画：安装文档工具依赖 Pillow 后运行 `python tools/build_readme_animation.py`。应用运行不依赖 Pillow。

## 封面生成提示词

```text
Use case: ads-marketing. Asset type: wide GitHub README cover illustration for PathCat, a Windows desktop file sidebar with a cat mascot. Create a charming polished kawaii editorial illustration, landscape 1536x1024. Warm cream background, soft sage and peach accents. Main character a small charcoal gray kitten with peach inner ears, round dark eyes, tiny pink nose, cream muzzle and chest, friendly proportions. Kitten sits beside neatly stacked golden file folders and a stylized desktop sidebar with folder shapes, playful dotted path connecting folders. Cozy helpful mood, clean spacious composition, subtle paper texture, rounded forms. Text verbatim: "PathCat" in large clear elegant rounded typography and small "Keep your files within reach." beneath it. No other text, no watermark. This is a promotional illustration, not an actual software screenshot.
```
