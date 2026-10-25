# Changelog

## 0.1.3

### Added
- Repository detection via `git rev-parse --is-inside-work-tree`; the panel now renders a dedicated "Create Git Repository" view when the project is not yet a Git repository.
- One-click repository initialization (`git init`) directly from the panel.
- VS Code-style staging: a per-file `+` button in the Changes list, plus a "Stage all" action.
- Unstaging via a per-file `-` button, including support for repositories with no commits yet.
- Commit workflow with a persistent message buffer, empty-message validation, and immediate status refresh after commit.
- Manual refresh button to force `git status` without waiting for the throttle interval.
- Files with dual status (e.g. `AM`) are now shown in both "Staged Changes" and "Changes", matching `git status` behavior.
- Branch display and switching.
- File status coloring (Modified / Added / Deleted / Untracked).
- Discard changes action for unstaged files.
- Push / Pull controls.
- Diff preview for tracked files.
- Asynchronous `git status` execution to keep the editor responsive on large repositories.

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

- Refactor example plugin name.