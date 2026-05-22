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
        carbon: '#0D0D0D',
        graphite: '#1A1A2E',
        'graphite-light': '#22223A',
        titanium: '#4A4A5A',
        'titanium-light': '#5A5A6E',
        aluminum: '#D0D0D8',
        'aluminum-dim': '#8A8A9A',
        orange: '#FF6B2B',
        'orange-dim': '#CC5522',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['Manrope', 'sans-serif'],
      },
      borderRadius: {
        bento: '12px',
      },
      boxShadow: {
        'orange-glow': '0 0 20px rgba(255, 107, 43, 0.3), 0 0 60px rgba(255, 107, 43, 0.1)',
        'card': '0 4px 24px rgba(0, 0, 0, 0.4)',
      },
      backgroundImage: {
        'crosshatch': "repeating-linear-gradient(45deg, rgba(255,255,255,0.012) 0px, rgba(255,255,255,0.012) 1px, transparent 1px, transparent 8px), repeating-linear-gradient(-45deg, rgba(255,255,255,0.012) 0px, rgba(255,255,255,0.012) 1px, transparent 1px, transparent 8px)",
      },
      animation: {
        'pulse-slow': 'pulse 3s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};