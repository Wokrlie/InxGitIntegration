# 更新日志

Git 集成插件的所有重要变更都记录在本文件中。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## 0.1.4

### 修复

- **项目文件夹不是 Git 仓库时面板直接崩溃。** 0.1.3 声称加入了「创建 Git 仓库」界面，但背后的渲染路径从未实现，打开非仓库项目会抛出 `AttributeError`。现在该界面已实现，并可在其中执行 `git init`。
- **面板作用在了错误的目录上。** `repo_path` 之前是 Editor 进程的工作目录，尽管代码注释写着「优先从引擎获取项目根」。现在改为解析 `project_context.get_project_root()`，只有在没有打开项目时才回退到工作目录。
- **窗口菜单里显示的是原始翻译键名。** 面板声明了一个翻译目录里根本不存在的标题键，而编辑器用 `t(title_key)` 解析面板标题，查不到时原样返回键名，于是菜单里直接显示了键名字符串。
- **点击手动刷新会多跑一次未节流的 `git status`。** 刷新按钮记录的是 `time.monotonic()` 时间戳，而节流比较用的是 `time.time()`，导致下一帧总是判定为「已过期」。
- **折叠标题会丢失展开状态。** 文件数量被编进了 ImGui 控件 ID，暂存一个文件就会让该区块重新展开。

### 变更

- 面板界面通过 `package/editor/translations.json` 支持英文与简体中文。此前所有可见文案都是硬编码英文，而中文使用页却暗示有中文界面。
- 提交按钮文案为「提交」，菜单路径文档统一为 `Extensions/Git Integration`。
- `runtime/` 不再附带占位的 `Null` 组件。本插件仅在编辑器中使用，不提供任何游戏运行时组件。
- 包简介改为描述实际功能集，并新增了中文本地化简介。

### 移除

- 状态重构后遗留的未使用状态 `files_status_list`。

### 文档

- README、更新日志与编辑器内使用页全部重写，与代码保持一致。中文 README 不再使用「插件模板」这一标题。
- 新增 `ROADMAP.md`、`CONTRIBUTING.md` 与 `RELEASING.md`。

## 0.1.3

> 下方提到的「创建 Git 仓库」界面在本版本中并未接通，实际是在 0.1.4 才完成的。

### 新增

- 使用 `git rev-parse --is-inside-work-tree` 检测仓库；项目尚未初始化 Git 时，面板会显示独立的「创建 Git 仓库」界面。
- 可在面板中一键初始化仓库（`git init`）。
- 仿 VS Code 的暂存操作：Changes 列表每个文件右侧提供 `+` 按钮，并提供「Stage all」整体暂存。
- 支持逐个文件取消暂存（`-` 按钮），兼容尚无任何提交的仓库。
- 提交流程：持久化提交消息缓冲区、空消息校验，以及提交后立即刷新状态。
- 手动刷新按钮，可绕过节流间隔强制执行 `git status`。
- 双状态文件（如 `AM`）现在会同时出现在「Staged Changes」与「Changes」中，与 `git status` 的行为一致。

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

### 变更

- 将示例名称替换为真实名称。
