# Releasing `seatlayer` to PyPI

Publishing checklist for the SeatLayer Python server SDK. This package has **never been
published** — the first upload permanently claims the name `seatlayer` on PyPI.

Everything below has been validated locally except the steps marked
**[needs a live account]**, which cannot be run until the account exists.

---

## 1. What the owner must create first

### PyPI account

| Item | Value |
|---|---|
| Registry | https://pypi.org (and https://test.pypi.org for the rehearsal) |
| Project name | `seatlayer` — verified **unclaimed** as of 2026-08-04 |
| Account | A PyPI account with **2FA enabled** (mandatory for all uploads since 2024) |
| Recovery | Save the 2FA recovery codes somewhere the team can reach them |

> **Name squatting is the one mistake nothing can undo.** If `seatlayer` is taken between now and
> the upload, the name is gone permanently — PyPI does not transfer names on request except in
> narrow dispute cases. If the sweep is going to be delayed, claim the name early with a `0.0.0`
> placeholder rather than waiting.

### Credential: pick ONE of these two paths

#### Path A — API token (simplest; right for a manual first publish)

1. PyPI → Account settings → **API tokens** → *Add API token*.
2. **First upload only:** the project does not exist yet, so a project-scoped token cannot be
   created. You must issue an **account-scoped** token (scope: *Entire account*).
3. Upload once (step 4 below). The project now exists.
4. **Immediately after:** create a new token scoped to **Project: seatlayer**, use that from then
   on, and **revoke the account-scoped token**. An account-scoped token can publish or yank *every*
   project you own; it should not outlive its one job.

Token format is `pypi-AgEIcHlwaS5vcmc…`. Use it with username `__token__`.

#### Path B — Trusted Publishing / OIDC (better long term; recommended once CI publishes)

No long-lived secret exists at all: PyPI mints a short-lived token for a specific GitHub Actions
workflow run. This is the better path and it is what the fleet should converge on, but note:

- It requires the GitHub repo `seatlayer/seatlayer-python` to **exist and be pushed** — it does not
  today (`git remote -v` points at it, but nothing has been pushed).
- Configure it as a **pending publisher** (PyPI → *Your projects* → *Publishing* → *Add a pending
  publisher*) so it works for the very first upload of a project that does not exist yet. You need:
  owner `seatlayer`, repo `seatlayer-python`, workflow filename (e.g. `release.yml`), and
  optionally a GitHub environment name.
- The publishing workflow needs `permissions: id-token: write` and
  `pypa/gh-action-pypi-publish@release/v1`. **No release workflow exists in this repo yet** — only
  `.github/workflows/ci.yml`. Writing it is a prerequisite for Path B.

**Recommendation:** use Path A for this first manual sweep, then move to Path B before 0.2.0.

---

## 2. Pre-flight (all verified locally on 2026-08-04)

```bash
cd python
python -m venv .venv && .venv/bin/pip install -e ".[dev]" build twine

.venv/bin/ruff check src tests     # → All checks passed!
.venv/bin/mypy                     # → Success: no issues found in 6 source files
.venv/bin/pytest -q                # → 33 passed
```

Confirm before building:

- [ ] `CHANGELOG.md` top entry reads `## 0.1.0 — 2026-08-04`. **If the sweep has slipped past that
      date, change it** — the date is baked into the sdist and shown on the PyPI page.
- [ ] `pyproject.toml` `version` and `src/seatlayer/__init__.py` `__version__` both read `0.1.0`.
      These are two separate literals with nothing enforcing agreement; check them by eye.
- [ ] Working tree is clean and the release commit is tagged (`git tag v0.1.0`).

---

## 3. Build and inspect

```bash
rm -rf dist
.venv/bin/python -m build
.venv/bin/twine check dist/*        # → PASSED for both artifacts
```

The wheel must contain **exactly** these seven package files plus `dist-info`:

```
seatlayer/__init__.py  client.py  errors.py  http.py  py.typed  resources.py  webhooks.py
seatlayer-0.1.0.dist-info/{METADATA,WHEEL,RECORD,licenses/LICENSE}
```

- `py.typed` **must** be present — without it every downstream mypy/pyright user silently loses all
  type information and sees `module is installed, but missing library stubs or py.typed marker`.
- No `tests/`, no `AGENTS.md`, no `.github/` in the wheel.
- The sdist deliberately **does** keep `tests/` (redistributors build from it) but must **not**
  contain `AGENTS.md` or `.github/`.

Verify the type marker actually works before uploading:

```bash
python -m venv /tmp/tc && /tmp/tc/bin/pip install dist/*.whl mypy
printf 'from seatlayer import SeatLayer\nreveal_type(SeatLayer("sk_test_x").mode)\n' > /tmp/c.py
/tmp/tc/bin/mypy --strict /tmp/c.py    # must reveal "str", NOT "Any"
```

---

## 4. Publish

Rehearse on TestPyPI first — it is a separate account and a separate token, and it is the only
way to see the rendered project page before the real name is spent.

```bash
# Rehearsal (needs a separate test.pypi.org account + token)
.venv/bin/twine upload --repository testpypi dist/*

# Real thing
.venv/bin/twine upload dist/*
# Username: __token__
# Password: pypi-AgEIcHlwaS5vcmc…
```

Non-interactive alternative:

```bash
TWINE_USERNAME=__token__ TWINE_PASSWORD='pypi-…' .venv/bin/twine upload dist/*
```

Then push the tag:

```bash
git push origin main --tags
```

---

## 5. Verify the published artifact

```bash
python -m venv /tmp/verify && cd /tmp/verify
bin/pip install seatlayer            # must resolve from PyPI, not a local path
bin/python -c "
import seatlayer, os
print(seatlayer.__version__)
print('typed:', os.path.exists(os.path.join(os.path.dirname(seatlayer.__file__), 'py.typed')))
c = seatlayer.SeatLayer('sk_test_x'); print(c.mode, c._http.base_url)
"
```

Expected: `0.1.0`, `typed: True`, `test https://api.seatlayer.io`.

Also eyeball https://pypi.org/project/seatlayer/ for:

- README rendering (Description-Content-Type is `text/markdown` — confirmed in the built metadata)
- License showing as **MIT** (PEP 639 `License-Expression`, not a wall of licence text)
- Author `SeatLayer <hello@seatlayer.io>`
- The five sidebar links: Homepage, Documentation, Changelog, Source, Issues
- The `Typing :: Typed` and Python 3.10–3.13 classifiers

---

## 6. If it goes wrong

**PyPI does not allow re-uploading a version.** Once `0.1.0` is up, that exact filename is spent
forever, even if you delete it. There is no `--force`.

| Situation | Action |
|---|---|
| Bad artifact, caught fast | `twine yank` is not a thing — yank in the web UI: project → *Manage* → *Releases* → *Yank*. Yanking hides it from new resolutions but keeps it installable for anyone who pinned it exactly. This is the correct, non-destructive fix. |
| Need a fixed build out | Bump to `0.1.1` and upload that. Never try to reuse `0.1.0`. |
| Leaked secret in the artifact | Yank **and** delete the release in the UI, then rotate the leaked credential. Assume it was already mirrored — deletion is not containment. |
| Wrong project entirely | Project → *Manage* → *Settings* → *Delete project*. Only possible while you are the sole owner; the **name is not released for reuse by others** immediately, but you also cannot re-upload the same version. |

Deleting is almost always the wrong reflex: it breaks anyone who already installed. **Prefer yank +
a patch release.**

---

## 7. Post-publish

- [ ] Revoke the account-scoped token; replace with a project-scoped one (Path A step 4).
- [ ] Add `Programming Language :: Python :: 3.14` to `pyproject.toml` **after** adding `3.14` to the
      CI matrix. The suite passes on 3.14.5 locally today, but the classifier should follow tested
      support, not precede it.
- [ ] Consider a `release.yml` + Trusted Publishing (Path B) before 0.2.0.
- [ ] Fleet nit, not a blocker: the `User-Agent` is the bare string `seatlayer-python` with no
      version, matching node/go/php/ruby. Once these are in customers' hands, support cannot tell
      which SDK version a request came from. Worth changing across all seven at once, never in one.
