# QuietPet 图片资源说明

本文件汇总 QuietPet（桌宠 + 侧边栏文件管理器）所需的**图片资源**：
已内置的 UI 图标包，以及“猫咪”相关的图片规格（当前为 Tk 直接绘制，可选替换为图片）。

---

## 1. 猫咪（桌面宠物）

### 当前实现：不需要图片
猫咪是用 **Tk Canvas 直接绘制**的（见 `quietpet/ui/pet.py` 的 `draw_cat()`），
圆形脸 + 两只耳朵 + 眼睛 + 鼻子 + 一个小点，全部用代码画出来。
好处：零图片依赖、可随时改颜色/大小；坏处：造型比较简陋。

### 如果想改成图片版（可选，推荐规格）

| 项目 | 要求 |
|---|---|
| 格式 | PNG，8-bit RGBA、非交错（程序用纯标准库解码） |
| 背景 | 透明 |
| 尺寸 | 建议 **96×96** 或 **128×128**（程序窗口为 80×98，按需缩放） |
| 命名 | 见下表，放在 `quietpet/assets/` 或项目根的 `Cursor_QuietPet_Icons/cat/` |

按“状态”准备不同形象（状态来自猫咪头顶的气泡）：

| 状态 | 含义 | 建议文件名 |
|---|---|---|
| idle | 空闲（可选眨眼/呼吸动画） | `cat_idle.png` |
| working | opencode 工作中 | `cat_working.png` |
| waiting | 等待确认/排队 | `cat_waiting.png` |
| offline | 读不到 opencode 状态 | `cat_offline.png` |

可选动画：每个状态用帧序列，如
`cat_working_0.png`、`cat_working_1.png` …
（帧数建议 ≤ 12，循环播放）。

> 状态气泡（“工作中/空闲/等待中/离线”）本身不需要图片，是文字 + 一个小圆点，
> 圆点颜色：工作中 `#f0a020`、空闲 `#5aa469`、等待中 `#e06c75`、离线 `#6b7079`。

---

## 2. UI 图标包（已内置）

目录：`Cursor_QuietPet_Icons/`

```text
Cursor_QuietPet_Icons/
├── 64px/     # 每个 64×64 PNG
├── 256px/    # 每个 256×256 PNG（高清）
└── README.md
```

| 文件名 | 用途 | 程序内名称 |
|---|---|---|
| `folder.png` | 普通文件夹 / “打开文件夹” | folder |
| `file.png` | 普通文件 | file |
| `new-file.png` | 新建文件 | new-file |
| `new-folder.png` | 新建文件夹 | new-folder |
| `refresh.png` | 刷新文件树 | refresh |
| `copy.png` | 复制 | copy |
| `search.png` | 搜索 | search |
| `settings.png` | 设置 / 技能分组 | settings |
| `mcp.png` | MCP 分组 | mcp |

### 程序如何使用
- 位置解析：`quietpet/ui/icons.py` 的 `resolve_icon_dir()` 会依次查找
  项目根的 `Cursor_QuietPet_Icons/`、冻结 exe 同级目录、当前工作目录。
- 优先用 `64px/`（找不到则用 `256px/`）。
- **自动着色**：原始图标是深灰线稿，程序会把不透明像素重着色为浅色 `#cfd3da`，以适配深色侧边栏。
- **渲染尺寸**：侧边栏 / 工具栏以 **16×16** 显示（盒式平均下采样，带抗锯齿）。
- 找不到图标包时会**自动回退**为内置的 emoji/符号。

### 添加 / 替换图标
1. 准备 PNG：8-bit RGBA、非交错、透明背景、建议 64×64 与 256×256 两套。
2. 按上表的**文件名**放入 `64px/` 与 `256px/`。
3. 若新增一种图标（非替换），在 `quietpet/ui/icons.py` 的 `ICON_NAMES` 里登记名字，
   并在 `quietpet/ui/explorer.py` 中使用。
4. 深色主题下无需自己上色，程序会自动改为浅色。

---

## 3. 分辨率与格式要求（统一）

| 项目 | 要求 |
|---|---|
| 格式 | PNG |
| 位深/通道 | 8-bit，RGB 或 RGBA（推荐 RGBA） |
| 交错 | 不支持（必须非交错） |
| 背景 | 透明 |
| 尺寸 | 图标 64/256；猫咪 96/128 |
| 颜色 | 图标建议单色线稿（程序会重着色）；猫咪保持原色 |

---

## 4. 快速检查清单

- [ ] `Cursor_QuietPet_Icons/64px/` 内 9 个 PNG 存在且命名正确
- [ ] （可选）猫咪图片按 4 种状态命名，透明 PNG
- [ ] 图标为透明背景、非交错 PNG
- [ ] 放入后重启 QuietPet 即可自动加载
