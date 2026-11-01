# Roadmap

Planned work for the Git Integration plugin. Delivered changes are recorded in [CHANGELOG.md](CHANGELOG.md) and [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md).

## Next

- **Discard changes** — revert the unstaged modifications of a single file.
- **Push / Pull controls** — fetch, pull, and push without leaving the Editor.
- **Diff preview** — show the content diff of a tracked file.

## Notes

Every item above has to keep the render thread responsive. Since 0.2.0 the panel runs every git command on a worker thread and draws the last snapshot it received, so the per-file operations follow the same pattern instead of blocking the frame. The status refresh is still throttled to one call per second, because a snapshot that is one second old is already too old to act on.

Adding an item to this file is welcome — open a pull request that describes the user problem it solves, not just the API it would use.
