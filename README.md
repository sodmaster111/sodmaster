# sodmaster

The Sodmaster Corporation

## Deployment notes

- Render uses the Python version pinned in `runtime.txt`. Update that file when
  the runtime needs to change.
- Configure the Render service (or your chosen host) with the `GIT_SHA`,
  `BUILD_TIME`, and `PY_RUNTIME` environment variables so the `/version` endpoint
  can expose accurate build metadata. The deploy workflow also publishes
  `app/version_env.json` as an artifact that can be mounted for offline
  environments.
- The marketing site under `app/site` is built with Astro for Render Static.
  - Set the `SITE_URL` environment variable to the final public hostname.
  - Use `cd app/site && npm install && npm run build` as the build command.
  - Publish the contents of `app/site/dist`.

## CI for site

The site deployment workflow (`.github/workflows/site-deploy.yml`) is disabled by default.
To enable it, add a repository secret named `ENABLE_SITE_CI` with the value `true`.

## SEO

- The marketing site ships `robots.txt` via `src/pages/robots.txt.ts` and generates `sitemap-index.xml`
  through the Astro sitemap integration.
- Run `node tests/site_seo_build.mjs` to verify the build emits both assets and that `robots.txt`
  links to the sitemap. This script is executed in CI as part of the default test suite.
```markdown
### Observability snapshot — 2025-10-25 08:59 UTC

- `GET /` → `{ "status": "ok", "service": "sodmaster", "docs": "/docs" }`
- `GET /healthz` → `{ "status": "ok" }`
- `GET /readyz` → `{ "status": "ok", "dependencies_ready": true }`
- `GET /version` → `{ "python": "3.11.12", "git_sha": "unknown", "build_time": "2025-10-25T08:59:21Z" }`
- `GET /ops/selftest`
  - `crew_tools=available`, `job_store=memory`, `redis_connected=false`
  - CGO: `POST /api/v1/cgo/run-marketing-campaign` → `202 Accepted` with `job_id=2636b95b-e930-4ed2-8da5-d977cdde656b`; poll `GET /api/v1/cgo/jobs/2636b95b-e930-4ed2-8da5-d977cdde656b` → `200 OK` & `status=done`
  - A2A: `POST /a2a/command` → `202 Accepted` with `job_id=82143796-b61a-4286-8fdd-e6c2cf32d7ad`; poll `GET /a2a/jobs/82143796-b61a-4286-8fdd-e6c2cf32d7ad` → `200 OK` & `status=done`

## WebDev API examples

Submit a site generation job:

```bash
curl -sS -X POST \
  http://localhost:8000/api/v1/webdev/generate-site \
  -H 'Content-Type: application/json' \
  -d '{
        "pages": [
          {"slug": "press/launch", "title": "Launch", "body": "# Launch\nAnnounce the release."}
        ],
        "components": [{"name": "PressHero"}],
        "layout_prefs": {"cta": {"href": "/contact/"}}
      }'
```

Poll the job status:

```bash
curl -sS http://localhost:8000/api/v1/webdev/jobs/<job_id>
```

Generate a payload from repository documentation:

```bash
curl -sS -X POST http://localhost:8000/api/v1/webdev/sync-content
```

### Startup logs
    2025-10-25 08:59:21,506 INFO Application startup | python_version=3.11.12 git_sha=unknown build_time=2025-10-25T08:59:21Z job_store=memory
    INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)

### Marketing site (Render Static)
- Service: `render.yaml` → `type: static`, name `sodmaster-site`, publishes `app/site/dist`
- `robots.txt`
    User-agent: *
    Allow: /
    Allow: /catalog/
    Allow: /catalog/*
    Disallow:
    Sitemap: https://sodmaster.online/sitemap-index.xml
- `sitemap-index.xml`
    <?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://sodmaster.online/sitemap-0.xml</loc></sitemap></sitemapindex>

### Prometheus metrics
- `http_requests_total`
    `/`=1 · `/healthz`=2 · `/readyz`=2 · `/version`=2 · `/api/v1/cgo/run-marketing-campaign`=1 · `/api/v1/cgo/jobs/2636b95b-e930-4ed2-8da5-d977cdde656b`=1 · `/a2a/command`=1 · `/a2a/jobs/82143796-b61a-4286-8fdd-e6c2cf32d7ad`=1 · `/ops/selftest`=1 · `/metrics`=1
- `cgo_jobs_total` — accepted=1 · running=1 · done=1
- `a2a_jobs_total` — accepted=1 · running=1 · done=1
```
