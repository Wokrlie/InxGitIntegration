# Infernux Git 集成

[Infernux 引擎](https://github.com/ChenlizheMe/Infernux)的版本管理面板。直接在编辑器里完成暂存、取消暂存和提交——不用切到终端。

[English](README.md) · [Infernux 引擎](https://github.com/ChenlizheMe/Infernux) · [插件开发文档](https://github.com/ChenlizheMe/Infernux/tree/master/docs) · [官方插件](https://github.com/ChenlizheMe/Infernux#plugins)

[![Validate and Release Plugin](https://github.com/Wokrlie/InxGitIntegration/actions/workflows/validate.yml/badge.svg)](https://github.com/Wokrlie/InxGitIntegration/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 功能

- 项目文件夹还不是仓库时，可一键执行 `git init`。
- 仿 VS Code 的暂存操作：每个文件右侧一个 `+` 按钮，外加**暂存全部**（等价于 `git add -A`）。
- 逐个文件取消暂存（`−` 按钮），仓库还没有任何提交时同样可用。
- 提交流程：消息缓冲区持久保留，空消息会被拦截。
- 文件列表自动刷新，并提供手动刷新按钮。
- 双状态文件（例如 `AM`）会同时出现在两个列表中，与 `git status` 的行为一致。
- 面板界面支持英文与简体中文。

## 环境要求

| 依赖 | 版本 |
| --- | --- |
| Infernux 引擎 | `>=0.4.1,<0.5` |
| Git | `PATH` 中可用的较新版本 |

Git 是**运行时依赖**。面板通过 `git` 可执行文件完成所有操作；Git 缺失时，面板会显示一条简短提示而不是文件列表。

## 安装

### 从发布页安装

1. 从 [Releases 页面](https://github.com/Wokrlie/InxGitIntegration/releases)下载 `wokrlie.git_integration.inxpkg`。
2. 在编辑器中打开 `扩展/插件`，安装下载的归档文件。

编辑器会对照 `package/inx_package.json` 中声明的引擎版本检查归档文件，并拒绝安装不兼容的版本。

### 从源码构建

```bash
python package.py build dist/wokrlie.git_integration.inxpkg
```

构建是确定性的——同一份源码构建两次会得到字节完全相同的归档文件。

## 使用

在菜单栏打开 `扩展/Git 集成`。面板作用于编辑器中当前打开的项目文件夹。

完整说明见 [`package/plugin_pages/usage.zh-CN.md`](package/plugin_pages/usage.zh-CN.md)，该文件也会随包发布，成为编辑器内的使用页。

## 故障排查

**面板提示当前环境无法使用 Git。** 系统没有安装 Git，或者 Editor 启动时的 `PATH` 里找不到它。安装 Git 后重启 Editor。

**点击提交没有任何反应。** 提交信息为空，需要先填写。

**`git commit` 报错询问你的身份。** Git 还没有配置用户信息，执行：

```bash
git config --global user.name "你的名字"
git config --global user.email "you@example.com"
```

**面板显示了预期之外的文件。** 面板跟随的是编辑器中打开的文件夹，而不是 Editor 程序所在的目录。

## 本地开发

```bash
python .infernux-dev/validate.py            # 检查包布局与 Python 源码
python -m unittest discover -s tests        # 校验与发布相关的契约测试
python package.py build dist/plugin.inxpkg   # 确定性构建
python package.py verify dist/plugin.inxpkg  # 校验构建产物
```

仅编辑器使用的代码位于 `package/editor/`，运行时接口位于 `package/runtime/`。`package/plugin_pages/` 存放编辑器内文档，每个英文页面都必须有对应的 `.zh-CN.md`——校验器会强制检查这一点。

## 文档

| 文档 | 用途 |
| --- | --- |
| [package/plugin_pages/usage.md](package/plugin_pages/usage.md) | 编辑器内使用说明（英文） |
| [package/plugin_pages/usage.zh-CN.md](package/plugin_pages/usage.zh-CN.md) | 编辑器内使用说明（简体中文） |
| [ROADMAP.md](ROADMAP.md) | 后续计划 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献与提交规范 |
| [RELEASING.md](RELEASING.md) | 发布流程 |

## 许可证

[MIT](LICENSE)。
