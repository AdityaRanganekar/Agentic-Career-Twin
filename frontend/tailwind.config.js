/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        canvas: {
          light: '#F3EEE3',
          card: '#FAF7F2',
          well: '#E8E1D3',
        },
        ink: {
          DEFAULT: '#111111',
          soft: '#2A2A2A',
          muted: '#666666',
        },
        terracotta: {
          DEFAULT: '#D9541E',
          hover: '#C24514',
          subtle: '#FCECE6',
        },
        alabaster: '#F3EEE3',
      },
      fontFamily: {
        display: ['"Space Grotesk"', '"Plus Jakarta Sans"', 'sans-serif'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        'crisp': '0 1px 3px rgba(17, 17, 17, 0.06)',
        'elevated': '0 4px 16px rgba(17, 17, 17, 0.08)',
        'hard': '2px 2px 0px #111111',
      }
    },
  },
  plugins: [],
};

