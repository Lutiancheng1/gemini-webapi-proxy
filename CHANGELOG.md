# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-06-23

### Added
- Pluggable cookie sources: `browser`, `env`, `file` (Netscape cookies.txt)
- Pluggable image downloader chain (5 strategies, configurable order)
- `BaseGeminiClient` interface with `WebAPIClient` reference adapter
- Optional `GOP_API_KEY` Bearer auth (off by default for local use)
- `/ready` health endpoint that probes the Gemini client
- Structured JSON logging (`GOP_LOG_FORMAT=json`)
- Image-generation refusals from upstream are now mapped to **HTTP 403**
  with the original Gemini message preserved, instead of a generic 500
- Plain-text upstream refusals ("I cannot fulfill this request.", "I'm
  unable to help with that request.", …) raised by chat-completion
  responses are detected and mapped to **HTTP 403** with an
  `UpstreamRefusalError`, so OpenAI clients no longer mistake them
  for successful answers
- `GOP_WEBAPI_MAX_RETRY` knob (default `1`) to cap the auto-retry
  behaviour of the underlying `gemini-webapi` RPC layer; surfaces real
  errors quickly instead of burning 5× the timeout
- English + Chinese README, full configuration & downloaders docs
- Project structure: `src/` layout, `pyproject.toml` (hatchling), `[project.scripts]`
- Test suite: 69 tests
- CI workflow: ruff + mypy + pytest matrix (Python 3.10/3.11/3.12, Ubuntu + macOS)
- Multi-platform Docker image published to `ghcr.io/Lutiancheng1/gemini-webapi-proxy`

### Changed
- All settings now use `GOP_` env prefix; old unprefixed names still work
  as legacy aliases
- HTTP errors now go through a single `map_api_error` mapper
- FastAPI app reorganised: routes split into `gemini_webapi_proxy.routes.*`
- `sync_runtime_env.py` now writes the **full** Safari cookie jar
  (35 cookies) to `GOP_GEMINI_COOKIES_RAW`, not just `__Secure-1PSID` /
  `__Secure-1PSIDTS`. Without the extras, the env-mode container
  was rejected by Gemini ("image creation isn't available").
- Dockerfile switched to `python:3.12-bookworm` (was `slim`); the slim
  image's OpenSSL 3.x is incompatible with the prebuilt `curl_cffi`
  aarch64 wheel, which throws `OPENSSL_internal: invalid library`.
- `docker compose` now uses `network_mode: host` (no more
  `host.docker.internal` magic, no port mapping needed)
- `scripts/docker-up.sh` now sets `GOP_BUILD_HTTP_PROXY` for the
  `docker build` step automatically

### Fixed
- `ModelRegistry.resolve_id()` no longer back-matches stable image
  aliases (e.g. `gemini-2.5-pro-image.aliases = ['gemini-3-pro']`).
  Without this guard, asking for `gemini-3-pro` could route to
  `gemini-2.5-pro-image` whenever the underlying model was missing
  from `_runtime` (e.g. transient `UNAUTHENTICATED` from Gemini),
  surfacing the misleading upstream error
  `Unknown model name: gemini-2.5-pro-image` against a request for
  the chat-only `gemini-3-pro` model.
- Dockerfile: stop building a pre-baked wheel in the builder stage and
  instead `pip install -e .` the live source tree in the runtime stage.
  The wheel path was copying `src` into a separate layer that could
  be served from cache even when the host source had changed, leading
  to stale code inside the image.
- Dockerfile: wrap the `apt-get` Chromium-deps layer in a 3-attempt
  retry loop. GitHub Actions runners occasionally hit
  `503 upstream connect error` from `deb.debian.org` mid-build,
  failing the job on a transient network blip that a single retry
  survives. Verified on the Docker workflow (CI run 28033739597).

### Removed
- Hard-coded path to `gemini-web-to-api/.env`
- Hard-coded Safari-first browser order on non-macOS platforms
- `ports:` and `extra_hosts:` from `docker-compose.yml` (replaced by
  `network_mode: host`)

### Security
- Cookie-file writes (`data/runtime.env`) are now `chmod 600`
- API key auth is opt-in; when unset, behaviour matches the previous
  local-only mode

### Verified end-to-end (2026-06-22)

Real traffic was driven through both the local venv and the Docker
container, using Safari cookies for the signed-in Gemini session:

| Path                                    | chat  | image      | notes |
|-----------------------------------------|-------|------------|-------|
| `venv` + `GOP_COOKIE_SOURCE=browser`    |  ✅   | ✅ 5.3 MB  | reference path |
| `docker compose` (bookworm) + `env`     |  ✅   | ✅ 4.8 MB  | what end users see |
| `docker compose` (slim, pre-fix)        |  ✅   | ❌ 500     | `curl_cffi` TLS error |

Sample prompts: "a simple red apple on white background" (venv), "a
tiny orange hexagon on white background" (Docker). Both returned real
PNG bytes (magic verified) within ~40s.

### Verified end-to-end (2026-06-23)

The curated 2-chat + 2-image model list (above) was re-verified through
both the Docker container and a local venv after the registry +
Dockerfile fixes:

| Path             | `gemini-3-flash` chat | `gemini-3-pro` chat | `gemini-2.5-flash-image` | `gemini-2.5-pro-image` |
|------------------|-----------------------|---------------------|--------------------------|-------------------------|
| Docker container | ✅                    | ✅                  | ✅ 5.5 MB apple          | ✅ 7.0 MB lemons         |
| venv (`-m`)      | ✅                    | ✅                  | ✅ 7.5 MB orange         | ✅ 8.2 MB succulent      |

All four images were real PNG bytes (magic verified, sample output
saved to `/tmp/gop-test/`). The image-prompts that previously
returned `Unknown model name: gemini-2.5-pro-image` now resolve
correctly to the underlying `gemini-3-pro` runtime entry.

### Project polish (0.1.0)

- README + README.zh: TOC, hero screenshot, "Why this project?" section,
  troubleshooting quick-reference inline.
- New `docs/architecture.md` with data-flow diagrams and registry
  internals.
- `examples/` rewritten with 4 runnable demos (chat, image, image-with-
  reference, Outsider Studio setup).
- GitHub metadata: 8 repository topics, expanded description, homepage
  URL pointing at `docs/`.
- Engineering: `CODEOWNERS`, `.editorconfig`, `.gitattributes`,
  `.pre-commit-config.yaml`, `.github/ISSUE_TEMPLATE/config.yml`,
  Dependabot for github-actions and pip.
- CONTRIBUTING.md now correctly references Python 3.11+ and
  pre-commit hook setup.
- `docs/zh/` empty directory removed.

## [Unreleased]

### Added
- (work in progress; this section is for unreleased changes)

## [0.0.1] - 2025-06-18

Internal preview, pre-release, not published to PyPI.
