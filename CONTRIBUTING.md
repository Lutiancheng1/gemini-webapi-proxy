# Contributing

Thanks for taking an interest in `gemini-openai-proxy`! This document
covers everything you need to send a useful PR.

## Development setup

```bash
git clone https://github.com/Lutiancheng1/gemini-openai-proxy
cd gemini-openai-proxy
python3 -m venv .venv
.venv/bin/pip install -e ".[browser-cookie,dev]"
.venv/bin/playwright install chromium
```

The first request from a freshly-installed dev environment can take up
to `GOP_INIT_TIMEOUT` seconds while the Gemini client initialises.

## Workflow

1. **Branch** off `main` for your change.
2. **Commit** with [Conventional Commits](https://www.conventionalcommits.org/):
   * `feat:` — new user-facing capability
   * `fix:` — bug fix
   * `docs:` — documentation only
   * `refactor:` — code change that neither fixes a bug nor adds a feature
   * `test:` — test additions / fixes
   * `chore:` — build, CI, tooling
3. **Lint and test** before pushing:

   ```bash
   .venv/bin/ruff check src tests
   .venv/bin/ruff format --check src tests
   .venv/bin/mypy src
   .venv/bin/pytest tests -v
   ```

4. **Open a PR** against `main` and fill in the template.

## Coding conventions

* Python 3.10+ syntax (we test 3.10, 3.11, 3.12).
* `from __future__ import annotations` at the top of every module.
* Type hints on public functions.
* Module-level logger (`logger = logging.getLogger(__name__)`) instead
  of `print`.
* No hard-coded absolute paths. No hard-coded personal info.
* New env vars use the `GOP_` prefix.
* New public classes/functions get docstrings.

## Adding a new download strategy

See [docs/downloaders.md](docs/downloaders.md#adding-a-new-strategy).
In short:

```python
@register_downloader
class MyDownloader(BaseDownloader):
    name = "my-strategy"
    priority = 50
    async def try_download(self, image, *, cookies, settings, client):
        return None  # or bytes
```

## Adding a new cookie source

```python
@register_source
class MyCookieSource(BaseCookieSource):
    name = "my-source"
    async def load(self) -> CookieBundle:
        return CookieBundle(psid=..., psidts=..., extras={...})
```

Then activate with `GOP_COOKIE_SOURCE=my-source`.

## Tests

* Pure functions: `tests/unit/`
* FastAPI integration: `tests/integration/`
* Live tests (require a real Gemini session and are skipped in CI):
  mark with `@pytest.mark.live`

Aim for ~80% line coverage on `src/`; coverage runs in CI.

## Release process

* Releases are cut by the maintainer via GitHub Releases.
* The release tag triggers the publish workflow, which:
  1. builds sdist + wheel with `python -m build`
  2. uploads to PyPI via trusted publishing
  3. builds multi-platform Docker images and pushes to GHCR
* The `CHANGELOG.md` is updated with the version's notable changes
  before the release commit.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
By participating you are expected to uphold it.
