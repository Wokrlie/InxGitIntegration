# 更新日志

Git 集成插件的所有重要变更都记录在本文件中。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## 0.1.3

首个正式发布的版本。

### 新增

- 使用 `git rev-parse --is-inside-work-tree` 检测仓库；项目尚未初始化 Git 时，面板会显示独立的「创建 Git 仓库」界面。
- 可在面板中一键初始化仓库（`git init`）。
- 仿 VS Code 的暂存操作：Changes 列表每个文件右侧提供 `+` 按钮，并提供「Stage all」整体暂存。
- 支持逐个文件取消暂存（`-` 按钮），兼容尚无任何提交的仓库。
- 提交流程：持久化提交消息缓冲区、空消息校验，以及提交后立即刷新状态。
- 手动刷新按钮，可绕过节流间隔强制执行 `git status`。
- 双状态文件（如 `AM`）现在会同时出现在「Staged Changes」与「Changes」中，与 `git status` 的行为一致。
- 面板界面支持英文与简体中文，通过 `package/editor/translations.json` 提供。

### 修复

- 在 `on_enable` 中同步调用 `subprocess` 导致引擎崩溃；Git 探测改为首次渲染时惰性执行。
- 在仓库外或错误工作目录中执行 `git status` 时返回 `exit status 128`。
- 循环内 `+` / `-` 按钮标签重复导致的 ImGui ID 冲突（`duplicate visible item ID`）。
- 渲染中途抛异常导致 `Missing EndGroup()`；现通过 `try/finally` 保证 `end_group()` 一定被调用。
- `text_input` 每帧把值重置为占位文本，导致提交按钮无效。
- 「Stage all」按钮与折叠标题点击区域重叠导致无响应。
- 项目文件夹还不是 Git 仓库时面板无法渲染的问题；「创建 Git 仓库」界面已实现，并可在其中执行 `git init`。
- 面板现在作用于编辑器中打开的项目文件夹，而不是 Editor 进程的工作目录。
- 窗口菜单标签与面板标题改为使用已声明的翻译键；此前会直接显示原始键名。
- 手动刷新与自动刷新现在使用同一个时钟，点击刷新按钮不会再触发一次未节流的 `git status`。
- 文件数量变化时，折叠标题保持原有的展开状态。

### 变更

- 所有 Git 子进程调用现在都通过 `cwd=` 显式指定工作目录。
- 以 `staged_files`、`unstaged_files`、`untracked_files` 三个独立集合取代 `files_status_list`，允许同一文件同时处于多个状态。
- 状态解析改用 `git status --porcelain`，并以原子方式更新列表；临时失败时保留上一次的已知状态。
- `git status` 刷新节流为每秒最多一次，避免每帧启动子进程。
- 提交按钮文案改为「提交」，面板上所有可见文案均已本地化。
- `runtime/` 不再附带占位的 `Null` 组件。本插件仅在编辑器中使用，不提供任何游戏运行时组件。

### 移除

- 状态重构后遗留的未使用状态 `files_status_list`。

## 0.1.2

### 变更

- 将示例名称替换为真实名称。
