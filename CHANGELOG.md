# Changelog

All notable changes to the Git Integration plugin are documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.2.0

### Added

- **Branch management from the panel.** A **Branches** section in the panel shows the branch the project is on — with its upstream and how far it has drifted from it (`↑2 ↓1`) — and lists the local branches together with the remote ones Git already knows about. The branches arrive together with the file lists in one background pass, so the list is always the one the repository actually has. Typing in the filter box narrows the list down; the filter only changes what is shown and runs no command.
- **Switching branches.** Clicking a branch selects it — the selected branch is marked with an arrow — and the actions below the list apply to it. **Checkout** switches to it with `git checkout`. The switch runs on a worker thread, so the panel stays responsive even in a large repository.
- **Creating a branch from the panel.** A row at the bottom of the section takes a new branch name and creates it from the current `HEAD`, then switches to it. The name is checked with `git check-ref-format --branch` before it is used, so Git itself decides what a valid branch name is, and a name starting with `-` is refused before it can reach a command line.
- **Deleting a branch.** **Delete** removes the selected branch and lets git refuse a branch whose commits were never merged. **Force delete** removes it anyway, and git's reflog still keeps those commits.
- **Renaming a branch.** **Rename** opens a field for the new name. The name is checked with `git check-ref-format --branch` first, so a name git would refuse never reaches the command.
- **The commit log of a branch.** The **Branch log** section lists the last 50 commits of the selected branch, newest first, each with its short hash and its subject. The log is fetched in the background, so a branch with a long history does not stall the frame.
- **A failure dialog that points at the Console.** A failed branch operation opens a modal with one sentence about what went wrong, a note that the full message was written to the Console, and three buttons: *Open Console*, *Copy details*, and *Close*. The common Git failures each get their own sentence — local changes that the switch would overwrite, a branch that no longer exists, an invalid name, a name that is already taken, and a branch that another worktree holds.

### Changed

- **Every git command now runs on a worker thread.** Status collection, staging, unstaging, committing, `git init`, the branch listing, the branch log, and the checkout itself all happen off the render thread, which only draws the last snapshot it received. A large repository no longer stalls the Editor, and a checkout that takes a while no longer freezes the frame.
- **The status comes from `git status --porcelain=v2 -z --branch`.** One call now returns the branch name, the upstream, the ahead/behind counters, and the file list, instead of the file list alone. The `-z` form keeps a path that is not plain ASCII literal, where the older format quoted it as an octal escape.
- **Git output is decoded as UTF-8 on purpose.** The panel no longer depends on the console code page of the machine it runs on, so Chinese commit messages and Chinese file names survive on a Windows that is not running in UTF-8.
- Every call to `git` now lives in the new `package/editor/wokrlie/git_integration/git.py` module, so the panel no longer talks to `subprocess` itself. That module never touches the Engine API, which is what makes it safe to call from a worker thread.
- **The panel runs no git command on the render thread at all.** Whether git is usable is answered by the exit code of the status command instead of a separate `git --version` probe, and a branch name is validated on the worker thread instead of while the frame is being drawn.

### Fixed

- **The panel reported Git failures as Python tracebacks instead of the real error.** Every failure path called `Debug.error(...)`, which is not an Engine API — the Engine provides `Debug.log_error`. The call raised `AttributeError` before the Git message could be logged, so the reason a commit, a stage, or `git init` failed never reached the Console. The errors are now written with `Debug.log_error(...)` and tagged with the plugin's source, so the Console can group and clear them. The entry quotes the command line, the exit code, and Git's own message, so the failure can be reproduced by hand.
- **Unstaging a file raised `TypeError: 'function' object is not subscriptable`.** The action passed a function where the command factory expects the argument list of a git command, and the factory reads the first argument to name the worker thread, so the file was never unstaged. `git reset HEAD -- <path>` unstages it on its own, and it also works in a repository that has no commit yet: git falls back to the empty tree and the file returns to being untracked.
- **Non-ASCII file names were shown as octal escapes.** The old parser read the v1 porcelain format, in which Git quotes a path that is not plain ASCII, so a file called `文档/说明.md` appeared as `"\346\226\207..."`. The panel now reads the `-z` format, where the path is written literally.

### Requirements

- **Git 2.13 or newer.** `git status --porcelain=v2` needs Git 2.11, and the `%(upstream:short)` field of `git for-each-ref` needs Git 2.13. Both are from 2016 and 2017; any current distribution is well past them.

## 0.1.5

### Added

- Vector icons across the panel. The stage, unstage, stage-all, and refresh controls are now Lucide icons instead of the `+`, `-`, and `⟳` characters, and every file row leads with an icon for its kind of change.
- Coloured file status. The Git status code of each file is now drawn in the colour of that change — added is green, modified is yellow, deleted is red, untracked is cyan, renamed is blue, and a conflict is orange.
- Tooltips on the icon controls and on the status code, naming the action and the kind of change.
- A **License** page in the plugin information, which carries the plugin's own MIT licence and the notices for the bundled icon artwork.
- `package/plugin_pages/LICENSE` ships the plugin's licence inside the archive, and `package/plugin_pages/license.md` reproduces that licence together with the third-party notices as the plugin's License page. ISC and MIT both require their notice to travel with every copy, so a notice that only lived in the repository would not satisfy them.

### Changed

- The icon artwork is embedded in the plugin and rasterized at runtime through the Engine's LunaSVG backend. The package stays a single deterministic archive, and one vector asset can be drawn in any colour.
- The status code keeps its Git spelling, so a dual state such as `AM` stays readable next to its icon.

### Dependencies

- **The panel now depends on an undocumented Engine capability.** The icons are rasterized at runtime through the Engine's LunaSVG-backed texture loader, which is not part of the documented plugin API. Vector artwork could not previously be shipped inside a plugin at all, because ImGui only draws raster textures.
- If that capability is removed or changed in a future Engine release, the icons stop rendering and the panel falls back to text-only controls. Everything else in the panel keeps working, and the status codes stay readable.
- The plugin needs no build-time conversion step and no pre-rendered PNG per colour, but it does need an Engine release that still ships the SVG rasterizer.

## 0.1.4

### Fixed

- **The panel crashed in every project that was not a Git repository.** 0.1.3 announced a "Create Git Repository" view, but the render path behind it was never implemented, so opening a project outside a repository raised `AttributeError`. The view now exists and `git init` runs from it.
- **The panel operated on the wrong folder.** `repo_path` was the Editor process working directory, even though the code comment claimed it preferred the Editor's project root. It now resolves `project_context.get_project_root()` and falls back to the working directory only when no project is loaded.
- **The Window-menu label rendered a raw translation key.** The panel declared a title key that was never present in the translation catalog. The Editor resolves panel titles with `t(title_key)`, which returns the key unchanged when it is missing, so the menu showed the literal key name.
- **Clicking the manual refresh ran an extra unthrottled `git status`.** The refresh button stored a `time.monotonic()` timestamp while the throttle compared against `time.time()`, so the next frame always looked stale.
- **Collapsing headers lost their open state.** The file count was part of the ImGui widget ID, so staging a file reopened the section.

### Changed

- The panel UI is localized in English and Simplified Chinese through `package/editor/translations.json`. Every visible string was previously hardcoded English, while the Chinese usage page implied a Chinese UI.
- The commit button reads "Commit", and the menu path is documented as `Extensions/Git Integration`.
- `runtime/` no longer ships the placeholder `Null` component. The plugin is editor-only and exposes no gameplay components.
- The package summary now describes the feature set, and has a localized Chinese variant.

### Removed

- The unused `files_status_list` state left over from the status refactor.

### Documentation

- The README, changelog, and in-editor usage pages were rewritten to match the code. The Chinese README no longer carried the "plugin template" title.
- Added `ROADMAP.md`, `CONTRIBUTING.md`, and `RELEASING.md`.

## 0.1.3

> The "Create Git Repository" view announced below was not wired up in this version. It was completed in 0.1.4.

### Added

- Repository detection via `git rev-parse --is-inside-work-tree`; the panel renders a dedicated "Create Git Repository" view when the project is not yet a Git repository.
- One-click repository initialization (`git init`) directly from the panel.
- VS Code-style staging: a per-file `+` button in the Changes list, plus a "Stage all" action.
- Unstaging via a per-file `-` button, including support for repositories with no commits yet.
- Commit workflow with a persistent message buffer, empty-message validation, and immediate status refresh after commit.
- Manual refresh button to force `git status` without waiting for the throttle interval.
- Files with dual status (e.g. `AM`) are now shown in both "Staged Changes" and "Changes", matching `git status` behavior.

### Fixed

- Engine crash caused by calling `subprocess` synchronously from `on_enable`; Git detection is now performed lazily during the first render.
- `exit status 128` when `git status` was executed outside a repository or in the wrong working directory.
- Duplicate ImGui item IDs (`duplicate visible item ID`) caused by repeated `+` / `-` button labels inside loops.
- `Missing EndGroup()` errors when rendering was interrupted by an exception; `end_group()` is now guaranteed via `try/finally`.
- Commit button being a no-op because `text_input` reset its value to a placeholder every frame.
- "Stage all" button not responding due to overlapping with the collapsing header's hit area.

### Changed

- Working directory is now always passed explicitly via `cwd=` to every Git subprocess.
- `files_status_list` replaced with three independent collections (`staged_files`, `unstaged_files`, `untracked_files`), allowing a single file to appear in multiple states simultaneously.
- Status parsing now uses `git status --porcelain` and updates the lists atomically, preserving the last known state on transient failures.
- `git status` refresh is throttled to once per second to avoid spawning a subprocess every frame.

## 0.1.2

### Changed

- Replaced the example plugin name with the real name.
