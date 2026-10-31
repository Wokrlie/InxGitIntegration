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
- Every `git` call must pass `cwd=` explicitly so the panel always operates on the folder open in the Editor.
- Use `subprocess.run` with a timeout. The render thread must never block indefinitely.
- Panel state that survives a render lives on the instance; it is never stored in a module-level global.
