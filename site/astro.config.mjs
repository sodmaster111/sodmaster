import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  site: 'https://sodmaster.online',
  base: '/',
  output: 'static',
  integrations: [tailwind()],
  build: {
    inlineStylesheets: 'auto'
  }
});
