export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'brand-dark': '#0A0E27',
        'brand-purple': '#667eea',
        'brand-blue': '#00D9FF',
        'brand-gray': '#1a1f36',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Poppins', 'sans-serif'],
      }
    }
  }
}
