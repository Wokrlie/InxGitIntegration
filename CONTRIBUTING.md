# Contributing

Thanks for helping improve the Git Integration plugin.

## Getting set up

The project has no third-party dependencies — the Python standard library is enough.

```bash
git clone git@github.com:Wokrlie/InxGitIntegration.git
cd InxGitIntegration
python .infernux-dev/validate.py
python -m unittest discover -s tests
```

## Branches

- `main` — released code. Every commit here has passed CI.
- `dev` — the integration branch. Feature work lands here through a pull request.

## Commit messages

Use a short imperative subject line, optionally with a conventional-commit prefix:

```
feat: add branch switching to the panel
fix: keep the commit message buffer across renders
docs: align the usage page with the panel layout
```

The prefix set is `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `build`, `ci`.

## Before you open a pull request

Run the checks that CI runs:

```bash
python .infernux-dev/validate.py
python -m unittest discover -s tests
python package.py build dist/plugin.inxpkg && python package.py verify dist/plugin.inxpkg
```

## Documentation rules

- Every English page under `package/plugin_pages/` needs a matching `.zh-CN.md` file. The validator rejects the package otherwise.
- Keep the two languages in sync — a change to `usage.md` needs the same change to `usage.zh-CN.md`.
- User-visible strings belong in `package/editor/translations.json`, not inline in the panel. Both locales must declare the same key set, and every key must be namespaced under `wokrlie.git_integration.`.
- Record new work under an `## Unreleased` heading in both `CHANGELOG.md` and `CHANGELOG.zh-CN.md`.

## Code conventions

- The Editor half of the plugin lives in `package/editor/`, the player-facing half in `package/runtime/`. Runtime code must not import Editor modules; the validator enforces that boundary.
- Every `git` call lives in `package/editor/wokrlie/git_integration/git.py`. The panel must not run a git command itself — that module is the only place that knows how git is invoked, how its output is decoded, and how its output is parsed.
- Every `git` call must pass `cwd=` explicitly so the panel always operates on the folder open in the Editor.
- Git commands run on a worker thread, never on the render thread. `GitCommand` in `git.py` starts one and the render thread only polls it for the result. A module in `git.py` must never touch the Engine API, because it also runs off the render thread.
- Use `subprocess.run` with a timeout. The render thread must never block indefinitely.
- Panel state that survives a render lives on the instance; it is never stored in a module-level global.

## Icons and artwork

- Icons come from [Lucide](https://lucide.dev), which is free for commercial use under the ISC License. The geometry lives in `package/editor/wokrlie/git_integration/icons.py`.
- Icons are embedded in the module rather than shipped as files, so the plugin never depends on where its package is unpacked and the build stays byte-for-byte deterministic.
- Any new artwork must come from a permissive licence and be recorded in `package/plugin_pages/license.md` before it ships. That page is the plugin's License page in the editor, so the notice travels with every installed copy.
- The icons are rasterized at runtime through the Engine's LunaSVG backend. ImGui itself cannot draw SVG, so do not expect the vector source to reach the renderer.
