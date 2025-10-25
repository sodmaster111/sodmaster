# CGO Marketing Crew

The CGO Marketing crew operates the strategy, content production, and distribution loops
for Sodmaster's growth programs. The crew coordinates with WebDev to publish landing pages
and keeps CGO leadership informed through KPI dashboards.

## Roles

- **Strategist** — Owns ICP insight, messaging hierarchy, and campaign KPIs.
- **ContentLead** — Produces briefs and content packages (articles, posts, landing outlines).
- **Distribution** — Plans channel roll-outs across Telegram Mini App, site blog, dev.to, X, and HackerNews.
- **Analyst** — Instruments UTM taxonomy and conversion metrics, feeding insights back to the Strategist.

## Deliverables

- `docs/campaign.json` — Canonical campaign blueprint with timeline, channel mix, and ownership notes.
- `docs/content/*.md` — Draft content packages ready for editorial review and PR hand-off.
- `app/site/src/data/posts.json` — Manifest consumed by the static site for marketing updates.
- WebDev PRs under `web/content-*` branches with landing page requirements.

## Workflow

1. Intake: receive `{goals, audiences, topics, cadence, channels}` via `/api/v1/mktg/plan`.
2. Strategist creates funnel-aligned content matrix and KPI guardrails.
3. ContentLead drafts markdown packages and briefs landing needs to WebDev.
4. Distribution generates channel-specific copy and timing.
5. Analyst attaches UTM/measurement plan and pushes metrics to Prometheus.
6. Optional `/api/v1/mktg/publish` call notifies downstream crews to ship landing pages.
