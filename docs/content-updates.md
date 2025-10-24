# Updating Sodmaster marketing content

The marketing site under `app/site` is built with [Astro](https://astro.build) and optimized for Render Static deployments.

## Local development

1. Install dependencies once:
   ```bash
   cd app/site
   npm install
   ```
2. Start the development server with hot reload:
   ```bash
   npm run dev
   ```
3. Visit `http://localhost:4321` to preview the catalog and landing pages.

## Editing catalog inventory

- Update product metadata in `app/site/src/data/products.json`.
- Each entry supports:
  - `slug`: URL path for the service (keep lowercase and hyphenated).
  - `title`, `summary`, and `price`: update copy as needed.
  - `tags`: short descriptors displayed as chips.
  - `heroImage`: full URL to a hosted image (Render Static serves it directly).
  - `seo`: optional overrides for description and keywords.
- To add a new service page, append a new object to the JSON file. The catalog index and dynamic `[slug].astro` route will render it automatically.

## Landing page content

- Primary hero, preview cards, and contact CTA live in `app/site/src/pages/index.astro`.
- Section headings and messaging can be edited inline within that file.

## SEO configuration

- Global layout metadata is controlled in `app/site/src/layouts/BaseLayout.astro`.
- The sitemap uses the site URL defined via the `SITE_URL` environment variable at build time (see deployment notes).
- `robots.txt` is generated in `app/site/src/pages/robots.txt.ts` and points to the sitemap index.

## Deployment workflow (Render Static)

1. Ensure the `SITE_URL` environment variable is configured in the Render service (e.g., `https://www.sodmaster.com`).
2. On Render, set the build command to `cd app/site && npm install && npm run build`.
3. Set the publish directory to `app/site/dist`.
4. Trigger a deploy—Render will serve the pre-rendered Astro site from the generated `dist/` folder.

## Accessibility & performance checks

Before publishing major updates:

- Run `npm run build` to confirm the static export succeeds.
- Use [Lighthouse](https://developers.google.com/web/tools/lighthouse) or PageSpeed Insights against the preview URL and address any regressions in performance, accessibility, or SEO scores.
