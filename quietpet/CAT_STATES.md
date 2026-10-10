# QuietPet 猫咪状态图（美术 / 生成规格）

给“猫咪”准备一整套状态图。程序当前用 Tk 直接绘制（无图），
本文件把需要的**状态、触发场景、画面建议、命名**列清楚，方便直接生成图片或交给美术。

---

## 0. 总规范

| 项目 | 要求 |
|---|---|
| 格式 | PNG，8-bit RGBA、**非交错**、透明背景 |
| 单帧尺寸 | 建议 **128×128**（或 96×96）；程序会缩放到画布内 |
| 画布/布局 | 宠物窗口约 **80×98**；上方约 20px 留给状态气泡，猫咪画在**中下部**，四周留透明边距 |
| 命名 | 小写 + 下划线，见各表“文件名”；动画帧加下标 `_0 _1 …` |
| 动画帧数 | 循环类建议 ≤ 12 帧；单次类 4–8 帧 |
| 颜色 | 猫咪保持原色即可（无需像 UI 图标那样重着色） |
| 放置目录 | `quietpet/assets/cat/`（建议新建；没有则回退到 Tk 绘制） |

> 状态气泡（工作中/空闲/等待中/离线）是**文字+圆点**，不需要图片。
> 圆点色：工作中 `#f0a020`、空闲 `#5aa469`、等待中 `#e06c75`、离线 `#6b7079`。

---

## 1. 基础状态（来自 opencode 状态）

| 状态 id | 触发场景 | 画面建议 | 文件名 | 动画 | 优先级 |
|---|---|---|---|---|---|
| `idle` | 空闲（已完成，等你输入） | 坐着，偶尔眨眼/呼吸 | `cat_idle.png` | 循环 4–8 帧 | **P0** |
| `working` | opencode 正在生成/执行 | 敲键盘/头上转圈/忙碌 | `cat_working.png` | 循环 6–12 帧 | **P0** |
| `waiting` | 有任务排队/等待确认 | 举爪/头顶“！” | `cat_waiting.png` | 循环 4–8 帧 | **P0** |
| `offline` | 读不到 opencode 状态 | 打瞌睡（Zzz）/问号 | `cat_offline.png` | 循环 4–8 帧 | **P0** |
| `sleeping` | 长时间空闲（可选） | 趴着睡 | `cat_sleeping.png` | 循环 4–8 帧 | P2 |

---

## 2. 拖动 / 悬停交互

| 状态 id | 触发场景 | 画面建议 | 文件名 | 动画 | 优先级 |
|---|---|---|---|---|---|
| `dragging` | 按住猫咪拖动（改宽度/换边） | 被拎起、四肢悬空、眼睛睁大 | `cat_dragging.png` | 循环 4 帧（轻微摇晃） | **P0** |
| `dropped` | 拖拽松手落地 | 落地小弹跳/尘土 | `cat_dropped.png` | **单次** 4–6 帧 | P1 |
| `hover` | 鼠标悬停在猫咪上 | 抬头看你 | `cat_hover.png` | 单次/循环 2–4 帧 | P1 |
| `click` | 单击猫咪（开合面板） | 眨眼/点头回应 | `cat_click.png` | 单次 4 帧 | P1 |
| `panel_open` | 侧边栏被打开 | 猫咪“钻到面板内侧边缘” | `cat_panel_open.png` | 单次 4–6 帧 | P1 |
| `panel_close` | 侧边栏收起 | 猫咪回到屏幕外边缘 | `cat_panel_close.png` | 单次 4–6 帧 | P1 |

---

## 3. 文件夹操作反馈

| 状态 id | 触发场景 | 画面建议 | 文件名 | 动画 | 优先级 |
|---|---|---|---|---|---|
| `file_in` | 从资源管理器拖文件进面板（复制） | 接住落下的文件 | `cat_file_in.png` | 单次 4–6 帧 | P1 |
| `file_move` | 面板内拖动文件到另一个文件夹（移动） | 抱着文件搬过去 | `cat_file_move.png` | 单次 4–6 帧 | P1 |
| `file_copy` | Ctrl 拖动（复制） | 文件“复制成两份” | `cat_file_copy.png` | 单次 4–6 帧 | P2 |
| `delete` | 移入应用回收区 | 把东西丢进盒子 | `cat_delete.png` | 单次 4–6 帧 | P1 |
| `new` | 新建文件/文件夹 | 变出一个小方块 | `cat_new.png` | 单次 4–6 帧 | P2 |
| `refresh` | 点击刷新 | 转圈/扫一遍 | `cat_refresh.png` | 单次 6 帧 | P2 |
| `error` | 操作失败（权限/重名…） | 皱眉/冒问号 `?` | `cat_error.png` | 单次 4 帧 | P1 |
| `success` | 操作成功 | 比 OK / 亮星星 | `cat_success.png` | 单次 4 帧 | P2 |

---

## 4. 技能（Skills）与 MCP

| 状态 id | 触发场景 | 画面建议 | 文件名 | 动画 | 优先级 |
|---|---|---|---|---|---|
| `skill_drag` | 拖出“技能”标签（拖出 `SKILL.md`） | 叼着一张技能卡片 | `cat_skill_drag.png` | 循环 4 帧 | P1 |
| `skill_copy` | 点击技能复制 `@ID` | 复制魔法/星星 | `cat_skill_copy.png` | 单次 4 帧 | P2 |
| `mcp_connect` | MCP 连接/使用 | 插头/线缆接上 | `cat_mcp.png` | 循环 4 帧 | P2 |
| `mcp_error` | MCP 连接失败 | 线缆打结/断线 | `cat_mcp_error.png` | 单次 4 帧 | P2 |

---

## 5. 最小可用集（先做这些就够）

**P0（必备）**：
`idle` · `working` · `waiting` · `offline` · `dragging` · `panel_open` · `panel_close`

**P1（推荐）**：
`dropped` · `hover` · `click` · `file_in` · `file_move` · `delete` · `error` · `skill_drag`

**P2（锦上添花）**：
其余（`sleeping / file_copy / new / refresh / success / skill_copy / mcp*`）。

---

## 6. 目录与命名

```text
quietpet/assets/cat/
├── manifest.json          # 状态清单（见下）
├── idle/
│   ├── cat_idle_0.png
│   └── cat_idle_1.png
├── working/
│   └── cat_working_0.png ...
├── dragging/
│   └── cat_dragging_0.png ...
└── ...
```

简化版（单帧即可）：直接把 `cat_<state>.png` 放在 `quietpet/assets/cat/`。

---

## 7. 触发映射（给开发接线用）

| 程序动作（代码位置） | 期望猫咪状态 |
|---|---|
| `pet.refresh_status()` 读到 kind | `idle/working/waiting/offline` |
| `pet._down`→`_move`（拖动中） | `dragging` |
| `pet._up`（松手） | `dropped`（随后回到基础状态） |
| 鼠标进入猫咪 | `hover` |
| 单机猫咪 / 双击 Alt 开合 | `panel_open` / `panel_close` |
| `explorer.on_os_drop`（外部拖入复制） | `file_in` |
| `explorer.drag_end`（内部移动） | `file_move`；Ctrl 时为 `file_copy` |
| `explorer.soft_delete` | `delete` |
| `explorer.new_folder/import_files` | `new` |
| 操作异常 `messagebox.showerror` | `error` |
| 技能标签拖出 | `skill_drag` |
| 技能标签单击（复制 `@ID`） | `skill_copy` |
| MCP 分组交互 | `mcp_connect` / `mcp_error` |

---

## 8. manifest.json 示例（可选，程序读取后启用图片版猫咪）

```json
{
  "canvas": [80, 98],
  "frame_ms": 120,
  "states": {
    "idle":     { "loop": true,  "frames": ["idle/cat_idle_0.png", "idle/cat_idle_1.png"] },
    "working":  { "loop": true,  "frames": ["working/cat_working_0.png"] },
    "waiting":  { "loop": true,  "frames": ["waiting/cat_waiting_0.png"] },
    "offline":  { "loop": true,  "frames": ["offline/cat_offline_0.png"] },
    "dragging": { "loop": true,  "frames": ["dragging/cat_dragging_0.png"] },
    "dropped":  { "loop": false, "frames": ["dropped/cat_dropped_0.png"] },
    "hover":    { "loop": true,  "frames": ["hover/cat_hover_0.png"] },
    "panel_open":  { "loop": false, "frames": ["panel/cat_panel_open_0.png"] },
    "panel_close": { "loop": false, "frames": ["panel/cat_panel_close_0.png"] },
    "file_in":   { "loop": false, "frames": ["files/cat_file_in_0.png"] },
    "file_move": { "loop": false, "frames": ["files/cat_file_move_0.png"] },
    "delete":    { "loop": false, "frames": ["files/cat_delete_0.png"] },
    "error":     { "loop": false, "frames": ["files/cat_error_0.png"] },
    "skill_drag":{ "loop": true,  "frames": ["skill/cat_skill_drag_0.png"] }
  }
}
```

---

## 9. 给图片生成器的提示词模板（可选）

> 一只极简风格的深灰色小猫咪，圆形脸、两只三角耳朵、白色小眼睛、粉色小鼻子；
> 透明背景，单只居中，全身可见；风格干净、扁平、和深色 UI 协调；
> 状态：**{状态描述：如“正在敲键盘/被拎起悬空/打瞌睡”}**；不要文字，不要边框，正方形 128×128。

统一要求：同一只猫在各状态里**造型一致**（比例、颜色、描边一致），只改动作/表情。
