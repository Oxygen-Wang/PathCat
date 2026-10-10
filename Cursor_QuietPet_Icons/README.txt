QuietPet | Windows 本地静默桌宠 + 文件夹管理器（右侧侧边栏）

运行：安装 Python 3（含 tkinter），双击“启动QuietPet.bat”。
      也可命令行：python QuietPet.py  或  python -m quietpet

呼出：默认“连按两次 Alt”打开/收起侧边栏；右键猫咪可改为其它连按手势（Shift/Ctrl/Win）
      或组合键（Ctrl+Alt+Q…）。
猫咪：贴在侧边栏内侧边缘、竖直居中。
      · 左右拖动 = 动态调整侧边栏宽度（拉宽/拉窄）；
      · 拖到屏幕另一半 = 换到左边/右边停靠；
      · 单击 = 开合侧边栏；右键 = 菜单（换文件夹/语言/快捷键/退出）。
      宽度、方向、位置都会保存。

侧边栏：停靠屏幕左或右、整屏高度；默认宽度 340（最小 260，可拖动猫咪调整）。
      顶部是路径标签栏（可放多个文件夹：切换 / × 移除 / ＋添加；把文件夹拖到猫咪上也可添加）。
      工具栏：打开文件夹 / 新建文件夹 / 新建文件 / 刷新 / 展开折叠切换（⊞↔⊟）。
      鼠标停在图标或条目上会显示提示。
技能(🧩)：在侧边栏**底部、从下往上**排列；默认收成一条长条（点 ▸/▾ 展开成多行）。
        最常用的前 5 个高亮排在最前（按钮上按“使用次数”排序，次数会保存）。
        右键 → “设置显示名…” 可给技能起中文名。
        停顿显示详情（id/名称/次数 + 说明 + SKILL.md 内容）。
        单击或拖出 = 文本 @技能ID（同时进剪贴板，可 Ctrl+V）；右键打开 SKILL.md。
MCP(🔌)：读取 opencode V2 的 mcp.servers，显示 名称 · 类型 · url/command ·(已禁用)。
文件操作（标准文件夹交互）：
      · 拖入：从资源管理器拖文件/文件夹到侧边栏 → 复制到当前文件夹。
      · 互拖：面板内拖到另一个文件夹 → 移动；按住 Ctrl 拖动 → 复制。
      · 复制/剪切/粘贴：Ctrl+C / Ctrl+X / Ctrl+V，或右键菜单。
      · 拖出：拖出面板到聊天窗口或任意程序，等同真实文件（CF_HDROP）。
      · 双击打开、F2 重命名、Delete 移入应用回收区、右键“复制路径”。
回收区：内容保存在“当前文件夹/.quietpet_trash”，可通过资源管理器恢复。
状态：猫咪头顶显示 opencode 当前状态（工作中/空闲/等待中/离线），只读本机数据库，不联网。
图标：Cursor_QuietPet_Icons/ 的 9 个 PNG，程序自动读取、按深色主题着色为浅色并以 16px 渲染
      （纯标准库解码，无需 Pillow）；找不到时回退为内置符号。
语言：右键猫咪 → “语言 / Language” 切换 中文/English；文案在 quietpet/locale/。
安全：只管理你添加/打开的文件夹，不会扫描/修改其它位置。
错误日志：若出现异常会写到 %APPDATA%\QuietPet\error.log。
测试：本目录运行  python -m unittest test_quietpet -v

代码结构（quietpet 包，按功能分文件夹）：
  quietpet/
    app.py            应用装配入口（猫咪+侧边栏+手势+停靠）
    core/
      config.py       路径、配色、设置读写
      util.py         文件名校验、重名、jsonc 解析
      i18n.py         语言切换
      locale/         文案：zh.py、en.py
    gestures/
      hotkey.py       全局手势（连按 Alt/Shift/Ctrl/Win 或组合键）
    native/
      win32.py        置顶、拖放源(OLE)、拖放目标(IDropTarget/DropTarget)、光标
    opencode/
      status.py       opencode 状态、技能、MCP 读取
    ui/
      pet.py          猫咪窗口与状态气泡
      explorer.py     侧边栏、树、技能标签、剪贴板、拖放、停靠
      widgets.py      悬停提示 ToolTip
      icons.py        PNG 图标解码/着色/缩放
    __init__.py / __main__.py
  QuietPet.py         仅启动入口（.bat / PyInstaller 用）

打包 exe：py -m pip install pyinstaller
然后：py -m PyInstaller --onefile --windowed --name QuietPet QuietPet.py
