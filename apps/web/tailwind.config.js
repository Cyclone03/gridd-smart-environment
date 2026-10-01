/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#14201f',
        canvas: '#f4f7f6',
        brand: { 50: '#ecfdf9', 500: '#0f8b7d', 600: '#0f766e', 700: '#115e59' },
      },
      boxShadow: { panel: '0 12px 32px rgba(15, 48, 44, 0.08)' },
    },
  },
  plugins: [],
};
