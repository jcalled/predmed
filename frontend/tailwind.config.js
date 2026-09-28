/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // PREDMED dark theme — idêntico ao protótipo HTML
        bg:       '#0A1628',
        surface:  '#0F1E35',
        surface2: '#152238',
        border:   'rgba(255,255,255,0.08)',
        accent:   '#00C2FF',
        accent2:  '#00FF9D',
        accent3:  '#FF6B35',
        red:      '#FF4444',
        yellow:   '#FFD700',
        text1:    '#E8EEF7',
        text2:    '#7A9CC4',
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['DM Mono', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(8px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}
