# Roadmap

Planned work for the Git Integration plugin. Delivered changes are recorded in [CHANGELOG.md](CHANGELOG.md) and [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md).

## Next

- **Branch display and switching** — show the current branch, and let the user switch or create branches from the panel.
- **File status coloring** — distinguish Modified / Added / Deleted / Untracked entries in both file lists.
- **Discard changes** — revert the unstaged modifications of a single file.
- **Push / Pull controls** — fetch, pull, and push without leaving the Editor.
- **Diff preview** — show the content diff of a tracked file.
- **Asynchronous `git status`** — move status collection off the render thread so large repositories do not stall the Editor.

## Notes

Every item above has to keep the render thread responsive. The panel currently shells out to `git` synchronously during rendering, with a one-second throttle between refreshes. Asynchronous status collection is listed last because it is the change that makes the rest cheap to add: once status collection no longer blocks the frame, per-file operations can follow the same pattern.

Adding an item to this file is welcome — open a pull request that describes the user problem it solves, not just the API it would use.
