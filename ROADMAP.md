# Roadmap

Planned work for the Git Integration plugin. Delivered changes are recorded in [CHANGELOG.md](CHANGELOG.md) and [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md).

## Next

- **Discard changes** — revert the unstaged modifications of a single file.
- **Push / Pull controls** — fetch, pull, and push without leaving the Editor.
- **Diff preview** — show the content diff of a tracked file.
- **Migrate the Git worker to an editor preload** — the panel starts daemon threads today, and the Engine cannot stop those deterministically. The plugin authoring guide recommends that long-lived background work lives in `editor/` and is owned by an `InxPreload`, with a registered cleanup that stops the worker and joins it within a bound; it shows that shape with a Flask service bound to loopback on an operating-system allocated port, with the development reloader disabled. The HTTP service itself is only worth building if something outside the Editor has to drive Git — the panel should keep talking to its worker in process.

## Notes

Every item above has to keep the render thread responsive. Since 0.2.0 the panel runs every git command on a worker thread and draws the last snapshot it received, so the per-file operations follow the same pattern instead of blocking the frame. The status refresh is still throttled to one call per second, because a snapshot that is one second old is already too old to act on.

Adding an item to this file is welcome — open a pull request that describes the user problem it solves, not just the API it would use.
