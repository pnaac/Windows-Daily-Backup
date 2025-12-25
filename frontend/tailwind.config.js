/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  darkMode: 'class', // Enables the Dark Mode toggle
  theme: {
    extend: {},
  },
  plugins: [require("daisyui")],
  daisyui: {
    themes: [
      {
        kriplani_light: {
          "primary": "#7c3aed", // Violet-600 (Modern Enterprise)
          "secondary": "#2dd4bf", // Teal-400 (Vibrant Accent)
          "accent": "#f472b6", // Pink-400 (Playful highlight)
          "neutral": "#1e293b", // Slate-800
          "base-100": "#ffffff",
          "base-200": "#f8fafc", // Slate-50
          "base-300": "#e2e8f0", // Slate-200
          "info": "#3b82f6",
          "success": "#10b981",
          "warning": "#f59e0b", // Amber-500
          "error": "#ef4444",
        },
        kriplani_dark: {
          "primary": "#a78bfa", // Violet-400
          "secondary": "#2dd4bf",
          "accent": "#f472b6",
          "neutral": "#1e293b",
          "base-100": "#0f172a",
          "base-200": "#1e293b",
          "base-300": "#334155",
          "info": "#60a5fa",
          "success": "#34d399",
          "warning": "#fbbf24",
          "error": "#fb7185",
        },
      },
    ],
  },
}