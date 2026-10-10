# QuietPet / Cursor 风格极简图标包

这是用于 Windows 本地文件夹侧边栏的 **9 款独立透明 PNG 图标**，参考极简开发工具的线性视觉风格设计，并非 Cursor 官方图标。

## 图标清单

| 文件名 | 用途 |
|---|---|
| `file.png` | 普通文件 |
| `folder.png` | 普通文件夹 |
| `new-file.png` | 新建文件 |
| `new-folder.png` | 新建文件夹 |
| `search.png` | 搜索 |
| `refresh.png` | 刷新文件树 |
| `copy.png` | 复制/克隆 |
| `mcp.png` | MCP 工具或连接入口（仅图标，不含 MCP 服务配置） |
| `settings.png` | 设置 |

## 目录结构

```text
Cursor_QuietPet_Icons/
├── 64px/       # 适合窗口、工具栏、小图标；每个 PNG 64×64
├── 256px/      # 高分辨率资源；每个 PNG 256×256
└── README.md
```

## 使用方法

1. 解压 ZIP。
2. 在程序中指定 `64px/` 或 `256px/` 目录里的对应图片。
3. 侧边栏建议渲染尺寸为 **16×16、18×18 或 20×20 CSS 像素**。
4. 图标透明背景，深灰图形，较适合浅色/浅绿色侧边栏；深色主题可通过代码换色或使用图像着色功能。

### HTML

```html
<button title="MCP"><img src="64px/mcp.png" width="20" height="20" alt="MCP"></button>
<button title="新建文件夹"><img src="64px/new-folder.png" width="20" height="20" alt="新建文件夹"></button>
```

### Python (Tkinter)

```python
import tkinter as tk

root = tk.Tk()
icon = tk.PhotoImage(file="64px/folder.png")
label = tk.Label(root, image=icon)
label.pack()
root.mainloop()
```

> 注意：此包仅包含 UI 图像素材与示例，不会创建真实文件、文件夹或 MCP 服务器。操作逻辑需要应用代码实现。
