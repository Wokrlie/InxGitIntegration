# Infernux Git Integration

A source control panel for the [Infernux Engine](https://github.com/ChenlizheMe/Infernux). Stage, unstage, and commit straight from the editor — no terminal required.

[简体中文](README.zh-CN.md) · [Infernux Engine](https://github.com/ChenlizheMe/Infernux) · [Plugin development docs](https://github.com/ChenlizheMe/Infernux/tree/master/docs)

[![Validate and Release Plugin](https://github.com/Wokrlie/InxGitIntegration/actions/workflows/validate.yml/badge.svg)](https://github.com/Wokrlie/InxGitIntegration/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- One-click `git init` when the open project folder is not a repository yet.
- VS Code-style staging: a `+` button per file, plus **Stage all** (equivalent to `git add -A`).
- Unstaging with a `−` button per file, including in repositories that have no commits yet.
- Commit flow with a persistent message buffer and empty-message validation.
- Automatic refresh of the file lists, plus a manual refresh button.
- Files with a dual status (for example `AM`) appear in both lists, matching `git status`.
- Localized panel UI in English and Simplified Chinese.

## Requirements

| Requirement | Version |
| --- | --- |
| Infernux Engine | `>=0.4.1,<0.5` |
| Git | A recent version available on your `PATH` |

Git is a **runtime requirement**. The panel shells out to the `git` executable; when it is missing, the panel shows a short notice instead of the file lists.

## Installation

### From a release

1. Download `wokrlie.git_integration.inxpkg` from the [Releases page](https://github.com/Wokrlie/InxGitIntegration/releases).
2. In the Editor, open `Extensions/Plugins` and install the downloaded archive.

The Editor checks the archive against the engine version declared in `package/inx_package.json` and refuses to install an incompatible build.

### From source

```bash
python package.py build dist/wokrlie.git_integration.inxpkg
```

The build is deterministic — two runs over the same source produce byte-identical archives.

## Usage

Open `Extensions/Git Integration` in the menu bar. The panel acts on the project folder currently open in the editor.

The full walkthrough lives in [`package/plugin_pages/usage.md`](package/plugin_pages/usage.md), which also ships inside the package as the in-editor usage page.

## Troubleshooting

**The panel reports that Git is not usable.** Git is not installed, or the Editor was started with a `PATH` that does not include it. Install Git and restart the Editor.

**Commit does nothing.** The commit message box is empty. Enter a message first.

**`git commit` fails asking who you are.** Git has no identity configured. Run:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

**The panel shows files you did not expect.** The panel follows the folder open in the Editor, not the folder the Editor binary lives in.

## Development

```bash
python .infernux-dev/validate.py            # package layout and Python sources
python -m unittest discover -s tests        # validation and release contracts
python package.py build dist/plugin.inxpkg   # deterministic build
python package.py verify dist/plugin.inxpkg  # verify a built archive
```

The Editor-only code lives in `package/editor/`, and the runtime surface in `package/runtime/`. `package/plugin_pages/` holds the in-editor documentation, and every English page must have a matching `.zh-CN.md` sibling — the validator enforces this.

## Documentation

| Document | Purpose |
| --- | --- |
| [package/plugin_pages/usage.md](package/plugin_pages/usage.md) | In-editor usage guide (English) |
| [package/plugin_pages/usage.zh-CN.md](package/plugin_pages/usage.zh-CN.md) | In-editor usage guide (Simplified Chinese) |
| [ROADMAP.md](ROADMAP.md) | Planned features |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution and commit conventions |
| [RELEASING.md](RELEASING.md) | Release procedure |

## License

[MIT](LICENSE).
