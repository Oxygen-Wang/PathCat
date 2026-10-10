# Changelog

All notable desktop changes are recorded here. Version numbers follow SemVer.

## [Unreleased]

### Documentation

- README 增加 AI 助手文件工作流的中英文介绍、使用场景与搜索关键词。

### Planned

- 后台文件传输、进度与取消。
- 文件操作撤销和回收区恢复入口。
- 多路径标签较多时的导航与布局优化。

## [0.2.0-beta.2] - 2026-10-10

### Changed

- 桌面小猫、侧栏、教学及提示采用普通窗口层级；仅用户点击或快捷键呼出时提升显示，不抢占其他软件。
- 当前源码删除 Codex/QuietPet 信息工具、插件、MCP 入口和本地控制端口。
- 文件树聚焦本地文件，移除 AI 技能和 MCP 配置栏目及外部任务状态轮询。
- 必要的小猫和图标资源完整纳入源码和桌面包；本地拖放测试图片不作为程序资源。

## [0.2.0-beta.1] - 2026-10-10

### Added

- 径猫 / PathCat 名称、桌面启动入口与 `--version`。
- 跨路径标签拖放、0.45 秒悬停切换、拖动目标提示、Ctrl 复制和 Esc 取消。
- 目标目录高亮、悬停展开和拖动边缘自动滚动。
- `.gitignore` / `.cursorignore` 显示过滤及规则编辑。
- 黑、白、暖米、柔和绿、灰蓝五套配色；8～20 字体大小。
- 可完成、跳过或重播的四步教学；预发布版本每次启动重播。
- Windows 自动测试、发布版本校验、Windows 可执行文件构建和 SHA-256 校验。

### Changed

- 默认快捷键迁移到 Ctrl+B，之后保留手动设置。
- 产品聚焦桌面文件侧栏；Codex 插件原型停止维护。
- VERSION 作为应用、标签、发布包的统一版本来源。

### Fixed

- 悬停切换路径后，源文件仍可移动至另一个已添加目录。
- 工具栏区域松手误操作、普通点击触发移动、父子条目重复传输。
- 配色和字体切换后保留侧栏显示状态与文件选择。
- 工作状态对应的猫咪动画；教学完成后移除常驻头顶文字。

## [0.1.0]

### Added

- QuietPet 原始桌宠与文件树、多目录管理、基础 Windows 拖放。
- 猫咪状态图片、停靠、技能标签和本地兼容控制通道。

[Unreleased]: https://github.com/Oxygen-Wang/PathCat/compare/v0.2.0-beta.2...HEAD
[0.2.0-beta.2]: https://github.com/Oxygen-Wang/PathCat/releases/tag/v0.2.0-beta.2
[0.2.0-beta.1]: https://github.com/Oxygen-Wang/PathCat/releases/tag/v0.2.0-beta.1
