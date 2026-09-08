import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        serif: ['Instrument Serif', 'Georgia', 'Times New Roman', 'serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        bg: {
          primary: '#09090b',
          secondary: '#0c0c10',
          tertiary: '#131318',
          card: '#18181b',
          'card-hover': '#1f1f25',
          input: '#111115',
        },
        accent: {
          DEFAULT: '#6366f1',
          hover: '#818cf8',
          glow: 'rgba(99,102,241,0.12)',
          'glow-strong': 'rgba(99,102,241,0.25)',
          subtle: 'rgba(99,102,241,0.06)',
        },
      },
      borderRadius: {
        xl: '16px',
        '2xl': '24px',
      },
      keyframes: {
        'fade-in-word': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        shimmer: {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-6px)' },
        },
        breathe: {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.4' },
          '50%': { transform: 'scale(1.2)', opacity: '0.7' },
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
        'think-scroll': {
          from: { transform: 'translateY(0)' },
          to: { transform: 'translateY(-50%)' },
        },
        'cursor-pulse': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.2' },
        },
      },
      animation: {
        'fade-in-word': 'fade-in-word 0.35s cubic-bezier(0.16,1,0.3,1) forwards',
        shimmer: 'shimmer 2s ease-in-out infinite',
        float: 'float 4s ease-in-out infinite',
        breathe: 'breathe 3s ease-in-out infinite',
        'pulse-dot': 'pulse-dot 2s ease-in-out infinite',
        'think-scroll': 'think-scroll 14s linear infinite',
        'cursor-pulse': 'cursor-pulse 1.2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}

export default config
