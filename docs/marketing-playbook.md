# Marketing Playbook

The Marketing crew maintains this playbook to keep strategy, production, and distribution
processes aligned.

## Content Matrix

| Funnel Stage | Primary Objective             | Recommended Assets           |
|--------------|-------------------------------|------------------------------|
| ToFu         | Awareness & narrative control | Thought leadership articles, AMA recaps |
| MoFu         | Education & evaluation        | Playbooks, comparison guides, webinars |
| BoFu         | Conversion & retention        | Case studies, ROI calculators, landing pages |

## KPI Benchmarks

- **Pipeline Contribution:** 30% of sourced opportunities attributable to marketing.
- **Conversion Rates:** Landing page CVR ≥ 8%, email nurture CTR ≥ 12%.
- **Engagement:** ≥ 3k monthly unique visitors on product stories, ≥ 2k MAU in Telegram Mini App.
- **Cadence:** Weekly ToFu story, bi-weekly MoFu asset, monthly BoFu proof point.

## SLA

- Campaign blueprint (`campaign.json`) within 4 business hours of intake.
- Draft content packages within 2 business days of plan approval.
- Distribution calendar published before the start of the cadence window.
- Publish hand-off to WebDev within 1 business day after `/api/v1/mktg/publish` is triggered.

## Measurement

- Use UTM schema: `utm_source={channel}`, `utm_medium=cgo`, `utm_campaign={slug}`.
- Push crew job metrics via Prometheus `crew_jobs_total{crew="mktg",status}`.
- Analyst delivers post-campaign readout within 5 business days of completion.
