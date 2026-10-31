# 更新日志

## 0.1.3

### 新增
- 使用 `git rev-parse --is-inside-work-tree` 检测仓库；项目尚未初始化 Git 时，面板会显示独立的「创建 Git 仓库」界面。
- 可在面板中一键初始化仓库（`git init`）。
- 仿 VS Code 的暂存操作：Changes 列表每个文件右侧提供 `+` 按钮，并提供「Stage all」整体暂存。
- 支持逐个文件取消暂存（`-` 按钮），兼容尚无任何提交的仓库。
- 提交流程：持久化提交消息缓冲区、空消息校验，以及提交后立即刷新状态。
- 手动刷新按钮，可绕过节流间隔强制执行 `git status`。
- 双状态文件（如 `AM`）现在会同时出现在「Staged Changes」与「Changes」中，与 `git status` 的行为一致。
### 计划
- 分支显示与切换。
- 文件状态着色（Modified / Added / Deleted / Untracked）。
- 未暂存文件的「放弃更改」（Discard changes）操作。
- Push / Pull 控制。
- 已跟踪文件的 Diff 预览。
- 异步执行 `git status`，在大仓库中保持编辑器响应。

### 修复
- 在 `on_enable` 中同步调用 `subprocess` 导致引擎崩溃；Git 探测改为首次渲染时惰性执行。
- 在仓库外或错误工作目录中执行 `git status` 时返回 `exit status 128`。
- 循环内 `+` / `-` 按钮标签重复导致的 ImGui ID 冲突（`duplicate visible item ID`）。
- 渲染中途抛异常导致 `Missing EndGroup()`；现通过 `try/finally` 保证 `end_group()` 一定被调用。
- `text_input` 每帧把值重置为占位文本，导致提交按钮无效。
- 「Stage all」按钮与折叠标题点击区域重叠导致无响应。

### 变更
- 所有 Git 子进程调用现在都通过 `cwd=` 显式指定工作目录。
- 以 `staged_files`、`unstaged_files`、`untracked_files` 三个独立集合取代 `files_status_list`，允许同一文件同时处于多个状态。
- 状态解析改用 `git status --porcelain`，并以原子方式更新列表；临时失败时保留上一次的已知状态。
- `git status` 刷新节流为每秒最多一次，避免每帧启动子进程。

## 0.1.2

- 重建插件引擎实例名称。
