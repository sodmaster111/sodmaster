import type { APIRoute } from 'astro';

const siteUrl = (import.meta.env.SITE as string | undefined) ?? 'https://example.com/';

const allowlist = ['/', '/catalog/', '/catalog/*'];

export const GET: APIRoute = () => {
  const normalizedSite = siteUrl.endsWith('/') ? siteUrl.slice(0, -1) : siteUrl;
  const body = [
    'User-agent: *',
    ...allowlist.map((path) => `Allow: ${path}`),
    'Disallow:',
    `Sitemap: ${normalizedSite}/sitemap-index.xml`
  ].join('\n');

  return new Response(body, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8'
    }
  });
};
