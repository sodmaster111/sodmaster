# WebDev Crew (Static Site Department)

The Web Development crew automates Astro site generation from structured JSON/Markdown payloads.
It consists of four specialist roles working in a deterministic pipeline:

- **WebArch** – information architecture, routing, SEO, and performance budgets.
- **Fullstack** – Astro/React implementation, data loaders, and page generation.
- **Infra** – Render Static deployment hygiene, CDN/cache strategy, robots/sitemap updates.
- **QA** – link checking, linting hooks, and Lighthouse CI (when enabled).

## Pipeline

The crew executes a five-step pipeline: `plan → scaffold → implement → validate → commit`.
Each invocation writes content to `app/site/src/pages/` and data manifests under
`app/site/src/data/generated/`.

1. **Plan** – outline navigation, assign role responsibilities, and calculate SEO/perf notes.
2. **Scaffold** – ensure page directories exist and map payload slugs to Astro files.
3. **Implement** – render `.astro` (or `.md`) pages and persist supporting JSON.
4. **Validate** – optionally run `npm ci && npm run build` (guarded by `ENABLE_SITE_CI`) and
   perform a lightweight link checker over `app/site/dist`.
5. **Commit** – return a JSON report suitable for PR descriptions.

Metrics are published to Prometheus:

- `crew_jobs_total{crew="webdev",status}`
- `crew_job_duration_seconds{crew="webdev"}`
- `http_requests_total{path="/site/build"}` when the build tool runs

Log events include `webdev_start`, `webdev_done`, and `webdev_failed` with JSON payloads.

## Payload schema

`POST /api/v1/webdev/generate-site` accepts the following payload:

```json
{
  "pages": [
    {
      "slug": "docs/getting-started",
      "title": "Getting Started",
      "body": "# Welcome\nUse this intro to orient customers.",
      "description": "Onboarding guide for the Sodmaster marketing site.",
      "tags": ["docs", "intro"],
      "layout": "BaseLayout",
      "format": "astro"
    }
  ],
  "components": [{"name": "Hero", "status": "stable"}],
  "layout_prefs": {"theme": "aurora", "cta": {"href": "/contact/"}}
}
```

Fields:

- `pages[]` – required list of Markdown/Astro page definitions. Supported `format` values:
  `astro`, `md`, or `markdown`. Unknown values raise a validation error.
- `components[]` – optional metadata stored in `src/data/generated/webdev-manifest.json`.
- `layout_prefs` – free-form JSON merged into the manifest.
- `job_id` – optional idempotency key (when provided as top-level field).

## Responses

- `202 Accepted` with `{ "job_id": "...", "status": "accepted" }` on enqueue.
- Poll `GET /api/v1/webdev/jobs/{id}` for status updates until `status` is `done` or `failed`.
- Completed jobs return the crew report as `result`.

## Syncing repository docs

`POST /api/v1/webdev/sync-content` builds a payload from `README.md` and every `docs/**/*.md`
file. Each page uses the Markdown format and is ready to feed into `generate-site`.

## Limitations

- Astro builds are skipped by default. Set `ENABLE_SITE_CI=1` in CI to run the full pipeline.
- Link checking performs a static crawl and does not resolve dynamic routes.
- Lighthouse CI integration is not automatic; the QA role records TODOs when unavailable.
