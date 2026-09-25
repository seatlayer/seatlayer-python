# Releasing `seatlayer` to PyPI

Releases are published by `.github/workflows/release.yml` through PyPI Trusted
Publishing (OIDC). No API token is stored in this repository or in its Actions
secrets: PyPI issues a short-lived token for the one workflow run.

## One-time setup

- The `seatlayer` project on PyPI lists this repository and `release.yml` as a
  trusted publisher.
- The publish job runs in the `pypi` GitHub environment. Add required reviewers
  to that environment if a tag push should wait for approval before publishing.

## Release steps

1. Update the version in **both** places, which must agree:
   - `pyproject.toml` (`version`)
   - `src/seatlayer/__init__.py` (`__version__`)
2. Add a dated entry at the top of `CHANGELOG.md`.
3. Run the gate locally:

   ```bash
   python -m venv .venv && .venv/bin/pip install -e ".[dev]" build twine
   .venv/bin/ruff check src tests
   .venv/bin/mypy
   .venv/bin/pytest -q
   ```

4. Merge the release commit to `main`, then tag it and push the tag:

   ```bash
   git tag v0.8.1 && git push origin v0.8.1
   ```

The workflow re-runs the gate, refuses to publish if the tag and either version
literal disagree, builds the sdist and wheel, checks that the wheel carries
`py.typed` and no `tests/` or `.github/` files, and then publishes.

## Verify

```bash
python -m venv /tmp/verify
/tmp/verify/bin/pip install seatlayer==0.8.1
/tmp/verify/bin/python -c "import seatlayer; print(seatlayer.__version__)"
```

Also check https://pypi.org/project/seatlayer/ for the rendered README, the MIT
license and the sidebar links.

## If a release is wrong

PyPI never accepts the same version twice, even after deletion.

- **Bad build:** yank it in the PyPI web UI (project, Manage, Releases, Yank) and
  publish a patch version. Yanking hides the release from new installs but keeps
  exact pins working.
- **Leaked secret in an artifact:** yank and delete the release, then rotate the
  credential. Assume it was already mirrored.
