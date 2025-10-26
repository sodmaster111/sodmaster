import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import icon from 'astro-icon';

export default defineConfig({
  site: 'https://sodmaster.online',
  integrations: [tailwind(), icon()],
  build: {
    inlineStylesheets: 'auto'
  }
});
