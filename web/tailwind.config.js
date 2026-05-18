/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
    "node_modules/primevue/**/*.{vue,js,ts}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // 悬疑小说主题配色
        noir: {
          50: '#f6f6f7',
          100: '#e2e4e8',
          200: '#c4c9d2',
          300: '#9da5b4',
          400: '#757d90',
          500: '#5a6275',
          600: '#474e5d',
          700: '#3a3f4b',
          800: '#31353e',
          900: '#2a2d35',
          950: '#1c1e24',
        },
        // 霓虹高亮色
        neon: {
          purple: '#a855f7',
          pink: '#ec4899',
          blue: '#3b82f6',
          cyan: '#06b6d4',
          amber: '#f59e0b',
        },
        // 氛围色
        fog: '#6b7280',
        blood: '#dc2626',
        mystery: '#1f2937',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        title: ['Clash Display', 'sans-serif'],
      },
      boxShadow: {
        'neon-purple': '0 0 20px rgba(168, 85, 247, 0.3)',
        'neon-blue': '0 0 20px rgba(59, 130, 246, 0.3)',
        'neon-pink': '0 0 20px rgba(236, 72, 153, 0.3)',
        'card': '0 4px 20px rgba(0, 0, 0, 0.4)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(168, 85, 247, 0.3)' },
          '100%': { boxShadow: '0 0 20px rgba(168, 85, 247, 0.6)' },
        },
      },
    },
  },
  plugins: [],
}
