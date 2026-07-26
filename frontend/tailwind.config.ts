// LinguaNotebook Tailwind Configuration — Bright & Beautiful
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Brand primary — warm indigo/violet
        primary: {
          50: "#F5F3FF",
          100: "#EDE9FE",
          200: "#DDD6FE",
          300: "#C4B5FD",
          400: "#A78BFA",
          500: "#8B5CF6",
          600: "#7C3AED",
          700: "#6D28D9",
          800: "#5B21B6",
          900: "#4C1D95",
          DEFAULT: "#7C3AED",
          foreground: "#FFFFFF",
        },
        // Success green
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
          DEFAULT: "#059669",
          foreground: "#FFFFFF",
        },
        // ⭐ BACKGROUND — warm white, never white-on-white
        background: {
          DEFAULT: "#FFFBEB",       // warm paper tint
          card: "#FFFFFF",           // pure white cards
          hover: "#F5F3FF",          // light purple hover
        },
        // ⭐ FOREGROUND — dark, high contrast
        foreground: {
          DEFAULT: "#1E293B",        // slate-800 — main text
          muted: "#475569",          // slate-600 — secondary text
          subtle: "#94A3B8",         // slate-400 — hints
        },
        // Surface (cards, modals)
        surface: {
          DEFAULT: "#FFFFFF",
          hover: "#F8FAFC",
          raised: "#FFFFFF",
        },
        // Muted backgrounds
        muted: {
          DEFAULT: "#F1F5F9",        // slate-100
          foreground: "#64748B",     // slate-500
        },
        // Borders
        border: {
          DEFAULT: "#E2E8F0",        // slate-200
          hover: "#CBD5E1",          // slate-300
          focus: "#7C3AED",          // purple
        },
        // Reading mode
        reading: {
          bg: "#FFFBEB",
          text: "#1E293B",
          highlight: "#FEF3C7",
        },
        // Streak (amber)
        streak: {
          DEFAULT: "#F59E0B",
          glow: "#FEF3C7",
        },
        // Destructive
        destructive: {
          DEFAULT: "#DC2626",
          hover: "#B91C1C",
          light: "#FEE2E2",
          foreground: "#FFFFFF",
        },
        // Success
        success: {
          DEFAULT: "#10B981",
          light: "#D1FAE5",
        },
        // Ring
        ring: {
          DEFAULT: "#7C3AED",
        },
        // ⭐ WHITE — explicit white token
        white: "#FFFFFF",
      },
      fontFamily: {
        heading: ['"Cormorant Garamond"', "Georgia", "serif"],
        body: ['"Crimson Pro"', "Georgia", "serif"],
        ui: ['"Inter"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', '"Fira Code"', "monospace"],
      },
      fontSize: {
        "display-lg": ["3.5rem", { lineHeight: "1.1", fontWeight: "700" }],
        display: ["3rem", { lineHeight: "1.15", fontWeight: "700" }],
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
        card: "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)",
        "card-hover": "0 4px 12px rgba(0,0,0,0.08)",
      },
      animation: {
        "fade-in": "fadeIn 200ms ease",
        "slide-up": "slideUp 300ms ease",
      },
      keyframes: {
        fadeIn: { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
