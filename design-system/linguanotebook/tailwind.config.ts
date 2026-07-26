// LinguaNotebook Tailwind Configuration
// Source: design-system/linguanotebook/MASTER.md
// Colors: Scholar Purple + Wisdom Green
// Typography: Cormorant Garamond / Crimson Pro / Inter

import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./frontend/src/**/*.{ts,tsx}",
    "./mobile/src/**/*.{ts,tsx}",
    "./shared/src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#FAF5FF",
          100: "#F3E8FF",
          200: "#E9D5FF",
          300: "#D8B4FE",
          400: "#A78BFA",
          500: "#8B5CF6",
          600: "#7C3AED",
          700: "#6D28D9",
          800: "#5B21B6",
          900: "#4C1D95",
          950: "#3B0764",
          DEFAULT: "#7C3AED", // --color-primary
          foreground: "#FFFFFF",
        },
        accent: {
          50: "#ECFDF5",
          100: "#D1FAE5",
          200: "#A7F3D0",
          300: "#6EE7B7",
          400: "#34D399",
          500: "#10B981",
          600: "#059669",
          700: "#047857",
          800: "#065F46",
          900: "#064E3B",
          DEFAULT: "#059669", // --color-accent
          foreground: "#FFFFFF",
        },
        surface: {
          DEFAULT: "#FFFFFF",
          hover: "#FAF5FF",
          raised: "#FFFFFF",
          dark: "#0F172A",
          "dark-hover": "#1E293B",
          "dark-raised": "#1E293B",
        },
        reading: {
          bg: "#FFFBEB",
          text: "#1E293B",
          highlight: "#FDE68A",
          annotation: "#E9D5FF",
          "bg-dark": "#0F172A",
          "text-dark": "#E2E8F0",
        },
        streak: {
          DEFAULT: "#F59E0B",
          glow: "#FEF3C7",
        },
        destructive: {
          DEFAULT: "#DC2626",
          hover: "#B91C1C",
          light: "#FEE2E2",
          "light-dark": "#7F1D1D",
        },
        success: {
          DEFAULT: "#10B981",
          light: "#D1FAE5",
          "light-dark": "#064E3B",
        },
      },
      fontFamily: {
        heading: ['"Cormorant Garamond"', "Georgia", "serif"],
        body: ['"Crimson Pro"', "Georgia", "serif"],
        ui: ['"Inter"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', '"Fira Code"', "monospace"],
      },
      fontSize: {
        "display-lg": ["3.5rem", { lineHeight: "1.1", fontWeight: "700" }],
        "display": ["3rem", { lineHeight: "1.15", fontWeight: "700" }],
        "heading-xl": ["2.25rem", { lineHeight: "1.2", fontWeight: "600" }],
        "heading-lg": ["1.875rem", { lineHeight: "1.25", fontWeight: "600" }],
        "heading-md": ["1.5rem", { lineHeight: "1.3", fontWeight: "600" }],
        "heading-sm": ["1.25rem", { lineHeight: "1.35", fontWeight: "600" }],
      },
      borderRadius: {
        sm: "0.375rem",
        md: "0.5rem",
        lg: "0.75rem",
        xl: "1rem",
        "2xl": "1.5rem",
      },
      boxShadow: {
        card: "0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05)",
        "card-hover":
          "0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.05)",
        "card-dark":
          "0 4px 6px -1px rgba(0,0,0,0.4)",
        "card-hover-dark":
          "0 10px 15px -3px rgba(0,0,0,0.5)",
      },
      animation: {
        "fade-in": "fadeIn 200ms ease",
        "slide-up": "slideUp 300ms ease",
        "card-flip": "cardFlip 500ms ease",
        "streak-pulse": "streakPulse 600ms ease infinite",
        "waveform": "waveform 1s ease infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        cardFlip: {
          "0%": { transform: "rotateY(0deg)" },
          "100%": { transform: "rotateY(180deg)" },
        },
        streakPulse: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(245, 158, 11, 0.4)" },
          "50%": { boxShadow: "0 0 0 8px rgba(245, 158, 11, 0)" },
        },
        waveform: {
          "0%, 100%": { transform: "scaleY(0.5)" },
          "50%": { transform: "scaleY(1)" },
        },
      },
      transitionDuration: {
        fast: "150ms",
        base: "200ms",
        slow: "300ms",
      },
      spacing: {
        "18": "4.5rem",
        "88": "22rem",
      },
    },
  },
  plugins: [],
};

export default config;
