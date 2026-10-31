# Changelog

All notable changes to the Git Integration plugin are documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
