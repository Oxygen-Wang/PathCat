# 版本管理规则 / Version policy

## 版本来源

`VERSION` 是唯一版本来源，应用读取此文件，打包必须包含它。
格式为 `MAJOR.MINOR.PATCH` 或 `MAJOR.MINOR.PATCH-beta.N`（也允许 alpha、rc）。
当前版本为 `0.2.0-beta.2`；不把测试版宣传为稳定版。

- 修复问题：增加 PATCH。
- 向后兼容的新功能：增加 MINOR，PATCH 归零。
- 不兼容变化：增加 MAJOR，MINOR / PATCH 归零。
- 同一预发布系列每次增加 N，例如 `beta.1` → `beta.2`。
- 每个版本必须有独立 CHANGELOG 条目；同一版本标签及发布包不得覆盖。

## 开发流程

1. 从最新 `main` 创建 `codex/<feature>` 或 `fix/<issue>` 分支。
2. 修改代码及对应验证；发布准备更新 VERSION 和 CHANGELOG。
3. 提交 PR，通过 `windows-tests` 检查；解决未关闭的评审讨论。
4. 通过 squash 合并。单人项目不强制另一人的批准，但仍要求 PR 和测试。
5. 本地同步 main；工作区必须干净：`git status --short`。
6. 运行 `python tools/check_version.py --tag v<version>`，并重新验证测试。
7. 为 **main 上经过测试的提交**建立附注标签：

   ```powershell
   git tag -a v0.2.0-beta.2 -m "PathCat 0.2.0-beta.2"
   git push origin v0.2.0-beta.2
   ```

8. 标签触发发布流程，重新测试、构建 Windows 包并发布 GitHub Release。
   预发布标签自动标记 Pre-release；包含版本 ZIP 和 SHA256SUMS.txt。

## 保护规则

GitHub `main` 规则要求 PR、最新的 windows-tests 和已解决的评审讨论，
禁止删除和强制推送，并要求线性历史。初次空仓库上传是唯一引导提交。
`v*` 标签禁止更新、删除；不要使用 `git tag -f` 或 `git push --force`。

已发布版本发现问题时，发布更高版本并说明原因；不修改原标签。
回退代码通过新的修复提交和 PR 完成，不重写 main 历史。

主分支只允许 squash merge，合并后删除开发分支。保护规则的实际启用状态
以 GitHub Settings → Rules 为准；不能把文档约定当作服务器已执行的规则。

## 发布范围

Windows 桌面文件侧栏是当前产品。插件原型已从当前源码删除，旧代码只保留
在 Git 历史中，不纳入桌面构建、不使用其独立旧版本号代表 PathCat 版本。

设置继续读取 QuietPet 的旧目录以保持升级兼容。测试版每次启动教学，
稳定版本只在未完成教学时自动显示。
