import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

const site = process.env.SITE_URL ?? 'https://sodmaster.online';

export default defineConfig({
  site,
  output: 'static',
  integrations: [
    sitemap({
      changefreq: 'weekly',
      priority: 0.7,
    })
  ],
  vite: {
    build: {
      target: 'es2019'
    }
  }
});
