# Changelog

All notable changes to the Git Integration plugin are documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.1.3

The first published release.

### Added

- Repository detection via `git rev-parse --is-inside-work-tree`; the panel renders a dedicated "Create Git Repository" view when the project is not yet a Git repository.
- One-click repository initialization (`git init`) directly from that view.
- VS Code-style staging: a per-file `+` button in the Changes list, plus a "Stage all" action.
- Unstaging via a per-file `-` button, including support for repositories with no commits yet.
- Commit workflow with a persistent message buffer, empty-message validation, and immediate status refresh after commit.
- Manual refresh button to force `git status` without waiting for the throttle interval.
- Files with dual status (e.g. `AM`) are now shown in both "Staged Changes" and "Changes", matching `git status` behavior.
- Localized panel UI in English and Simplified Chinese, shipped as `package/editor/translations.json`.

### Fixed

- Engine crash caused by calling `subprocess` synchronously from `on_enable`; Git detection is now performed lazily during the first render.
- `exit status 128` when `git status` was executed outside a repository or in the wrong working directory.
- Duplicate ImGui item IDs (`duplicate visible item ID`) caused by repeated `+` / `-` button labels inside loops.
- `Missing EndGroup()` errors when rendering was interrupted by an exception; `end_group()` is now guaranteed via `try/finally`.
- Commit button being a no-op because `text_input` reset its value to a placeholder every frame.
- "Stage all" button not responding due to overlapping with the collapsing header's hit area.
- The panel no longer fails to render when the open project folder is not a Git repository. The "Create Git Repository" view is implemented, and `git init` runs from it.
- The panel now follows the project folder open in the Editor instead of the Editor process working directory.
- The Window-menu label and the panel title resolve from a declared translation key instead of an undeclared one, which previously rendered the raw key.
- The manual refresh button and the automatic refresh use the same clock, so clicking the refresh button no longer causes an extra unthrottled `git status`.
- Collapsing headers keep their open state when the file counts change.

### Changed

- Working directory is now always passed explicitly via `cwd=` to every Git subprocess.
- `files_status_list` replaced with three independent collections (`staged_files`, `unstaged_files`, `untracked_files`), allowing a single file to appear in multiple states simultaneously.
- Status parsing now uses `git status --porcelain` and updates the lists atomically, preserving the last known state on transient failures.
- `git status` refresh is throttled to once per second to avoid spawning a subprocess every frame.
- The commit button reads "Commit", and the whole visible panel string set is translated.
- `runtime/` no longer ships the placeholder `Null` component. The plugin is editor-only and exposes no gameplay components.

### Removed

- The unused `files_status_list` state left over from the status refactor.

## 0.1.2

### Changed

- Replaced the example plugin name with the real name.
