# Releasing

Releases are produced by GitHub Actions. No artifact is uploaded by hand.

## Sources of truth

| What | Where |
| --- | --- |
| Plugin version | `package/inx_package.json` → `version` |
| Engine compatibility | `package/inx_package.json` → `engine` |
| Release notes | `CHANGELOG.md` and `CHANGELOG.zh-CN.md` |

The release tag must match the manifest version exactly — `v0.1.3` for version `0.1.3`. `package.py release-manifest` fails on any mismatch, so a mistyped tag stops the release instead of publishing a mislabelled archive.

## Procedure

1. Update `CHANGELOG.md` and `CHANGELOG.zh-CN.md`, and set the new version in `package/inx_package.json`.
2. Merge the change into `main` and wait for the `Validate and Release Plugin` workflow to go green on `main`.
3. Tag the merge commit and push the tag:

   ```bash
   git tag v0.1.3
   git push origin v0.1.3
   ```

4. The `release` job runs on the tag. It builds the archive, verifies it, checks that two independent builds are byte-identical, generates `infernux-plugin-release.json`, and publishes both files as GitHub Release assets.

## Published releases are immutable

A `reference` / `version` pair is a permanent identifier. Once a release exists, republishing the same version must fail rather than replace the archive that users have already installed.

The workflow enforces this by letting `gh release create` fail on a duplicate tag. `tests/test_release_immutability.py` runs the real publish step against a stub `gh` to prove that a duplicate release leaves both existing assets untouched.

Because of this, a fix for a published version needs a **new** version number. Never re-cut an existing tag.

## Artifact names

- Archive: `wokrlie.git_integration.inxpkg` — the manifest `reference` with `/` replaced by `.`.
- Release manifest: `infernux-plugin-release.json`.

## Verifying a release locally

```bash
python package.py build dist/wokrlie.git_integration.inxpkg
python package.py verify dist/wokrlie.git_integration.inxpkg
python package.py release-manifest dist/wokrlie.git_integration.inxpkg \
    --tag v0.1.3 --output dist/infernux-plugin-release.json
```

The build is deterministic: running it twice over the same source must produce byte-identical archives, which is what CI asserts before it publishes anything.
