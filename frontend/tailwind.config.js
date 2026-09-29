/** @type {import('tailwindcss').Config} */
// As cores apontam para as variáveis CSS de src/app/globals.css (fonte única
// dos tokens). Assim, trocar um valor lá muda Tailwind e estilos inline juntos.
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg:       'var(--bg)',
        surface:  'var(--surface)',
        surface2: 'var(--surface2)',
        surface3: 'var(--surface3)',
        border:   'var(--border)',
        'border-strong': 'var(--border-strong)',
        accent:   '#00C2FF', // hex (= --accent) para aceitar modificadores de opacidade (ex.: border-accent/25)
        accent2:  'var(--accent2)',
        accent3:  'var(--accent3)',
        red:      'var(--red)',
        yellow:   'var(--yellow)',
        text1:    'var(--text)',
        text2:    'var(--text2)',
        focus:    'var(--focus)',
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['DM Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      width: {
        sidebar: 'var(--sidebar-w)',
      },
      spacing: {
        sidebar: 'var(--sidebar-w)',
        topbar: 'var(--topbar-h)',
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
