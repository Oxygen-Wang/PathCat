> 已停止维护 / Archived. 当前产品为桌面文件侧栏 PathCat，此插件原型只保留历史记录。

# QuietPet Codex 本地插件

此插件连接本机 QuietPet，不需要 API Key。支持项目文件浏览、侧边栏开合和停靠、Codex 技能发现、显式任务状态报告。

## 0.2.0 实验性插件文件面板

0.4.0 增加五套整体配色与 `quietpet_theme`，桌面右键菜单和插件网页面板均可切换。默认快捷键改为 Ctrl+B，旧设置首次升级会迁移，之后保留手动修改。猫咪动画的任务状态映射也已修复。

0.3.0 改为直接复用项目及子目录的 `.gitignore` 和 `.cursorignore`。支持 `!` 例外、`**`、目录规则、转义及注释；两类文件分别判断，任意一类排除即隐藏。这只是显示规则应用，不查询 Git 的“是否已跟踪”状态，也不读取用户级 Git excludes。`.git` 目录默认隐藏。

右键/按钮“忽略”追加到根目录 `.cursorignore`；规则编辑器可选择 `.gitignore` 或 `.cursorignore`，保存直接写回所选文件并保留注释和空行。刷新时重新检查规则文件的修改时间。

增加 `quietpet_file_panel`，注册 MCP Apps 界面资源与聊天面板入口。兼容宿主可显示项目文件浏览、文本预览、拖动移动 / Ctrl 复制、忽略和恢复显示；不替换 Codex 原生文件树。

官方界面文档说明的是 ChatGPT / MCP Apps 兼容宿主；Codex 插件能加载工具，并不保证每个版本都渲染这个界面。
本机已验证 Codex CLI 0.154.0 可注册、安装并启用插件；当前聊天已能调用文件面板工具。
浏览器测试使用模拟 MCP Apps 宿主和真实临时文件，不能代替 Codex 内界面显示验证。

调用示例：“使用 QuietPet 插件打开当前项目的文件面板。”如果仅返回目录数据，说明该入口未显示界面，可使用原桌面侧边栏。

插件内拖放仅处理项目内部文件；系统文件导入及向其他软件拖出真实文件仍使用桌面面板。

## 已验证的本地安装方式

在项目根目录执行：

```powershell
python tools/package_codex_plugin.py
codex plugin marketplace add D:/AI/quietpet_local/plugins
codex plugin add quietpet-codex@quietpet-local
```

本地目录声明在 `plugins/.agents/plugins/marketplace.json`。更换项目路径时重新生成 `.mcp.json`，再注册新的本地源。启动更新版 GUI 后调用 `quietpet_file_panel`。

## 使用

1. 在项目根目录运行 `python tools/package_codex_plugin.py`。它生成当前电脑的 `.mcp.json` 和 `dist/QuietPetCodexPlugin.zip`。
2. 退出旧 QuietPet，再双击项目根目录的 `启动QuietPet.bat`，运行更新后的源码版本。现有 dist/QuietPet.exe 尚未重新打包。
3. 在支持手动本地插件安装的 Codex 中，选择插件目录 `plugins/quietpet-codex` 或导入 ZIP。不同版本的安装入口可能不同；没有本地安装入口时使用下方 MCP 接入。
4. 安装后新建聊天，选择 QuietPet 插件，发送：“连接 QuietPet 到当前项目，打开侧边栏并显示任务状态。”
5. 验证侧边栏项目路径正确，再发送：“把侧边栏移到左边”“列出当前项目文件”“列出 Codex 技能”。

## MCP 接入备用方式

没有本地插件导入入口时，可运行 `codex mcp add quietpet -- python D:/AI/quietpet_local/codex_mcp_entry.py`，然后重新打开聊天。MCP 注册只提供工具；需要把本包的 skills/quietpet 加入你的项目技能目录，或在聊天中明确要求调用状态工具，才能使用完整工作流。

## 边界

- 插件包的启动路径为当前电脑生成；项目移动或更换电脑后需要重新生成。
- GUI 必须在同一台电脑运行；不支持云端 Codex 操控本机桌面。
- 状态由技能主动报告，不会自动监听所有聊天、工具运行或审批事件。
- 最近一次状态报告生效，默认 300 秒过期后显示离线；多聊天状态聚合尚未实现。
- 文件读取只允许 GUI 管理的目录，解析真实路径以阻止 ../ 和链接越界。技能列表包含全局技能元数据。
- 不自动修改 Codex 用户配置，不发布到公共插件目录。
- 本机控制通道沿用项目现有 localhost 机制，没有身份认证；本包用于本地开发验证。
- 新面板操作也限定在 GUI 的当前项目内；禁止越界和递归拖放，重名时自动加后缀。
- Git wildmatch 解析使用项目内置 pathspec 0.12.1，许可证保存在 quietpet/_vendor/pathspec-0.12.1.dist-info/LICENSE。

官方插件格式参考：https://developers.openai.com/plugins/build/plugins
