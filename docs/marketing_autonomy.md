# Autonomous Marketing Department

The autonomous marketing department orchestrates a four-agent CrewAI pipeline that plans, produces, and analyses every weekly campaign.

## Architecture Overview

1. **StrategyAI** ingests the 12-week marketing plan and researches live trends via ExaSearch and Serper. It produces positioning, a thematic storyline, and a channel timeline for the current ISO week.
2. **CopyAI** selects MDX templates and composes English language assets for each channel. Every asset carries an A/B variant, call-to-action, and scheduling hint.
3. **DesignAI** prepares creative prompts for Leonardo or DALL-E based on the strategic theme and message focus. The prompts are stored alongside the copy assets.
4. **AnalystAI** evaluates the real-time metrics, decides the A/B winners, and issues tactical recommendations.

The crew operates sequentially: Strategy → Copy → Design → Analyst. The orchestrator also coordinates social channel clients, schedules future posts, and records campaign telemetry.

## Tooling & Metrics

- Channel integrations: Twitter, LinkedIn, Telegram, YouTube. Posts can be sent immediately or scheduled for future slots using an in-memory scheduler.
- Research: ExaSearch for deep trend analysis and Serper for SERP coverage.
- Prometheus metrics:
  - `marketing_posts_total{channel}` increments on every publication.
  - `marketing_clicks_total{channel}` captures new click volume for each channel.
  - `conversion_rate` reflects blended conversions / clicks across the crew.
  - `a_b_winner{experiment}` stores the winning variant code (1=A, 2=B).
- Weekly reports are persisted under `reports/marketing/YYYY-WW.json` with full strategy, creative, publishing, metrics, and insights context.

## Weekly Flow

1. `MarketingCrew.orchestrate_weekly_cycle(week)` loads the relevant plan entry, executes the agent pipeline, schedules/publishes posts, and gathers metrics.
2. `MarketingCrew.save_reports(week, report)` serialises the outcome for auditability.
3. AnalystAI insights can be retrieved via the `/api/v1/marketing/insights` endpoint for dashboards or leadership briefings.

The department operates autonomously yet remains observable: strategy inputs, creative outputs, and performance indicators are accessible to adjacent teams without manual coordination.
