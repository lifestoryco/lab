import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        "foreground-secondary": "var(--foreground-secondary)",
        "foreground-muted": "var(--foreground-muted)",
        surface: {
          DEFAULT: "var(--surface)",
          elevated: "var(--surface-elevated)",
          sunken: "var(--surface-sunken)",
          hover: "var(--surface-hover)",
          blue: "var(--surface-blue)",
          green: "var(--surface-green)",
          amber: "var(--surface-amber)",
          ivory: "var(--surface-ivory)",
          yellow: "var(--surface-yellow)",
        },
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        ring: "var(--ring)",
        primary: {
          50: "var(--primary-50)",
          100: "var(--primary-100)",
          300: "var(--primary-300)",
          400: "var(--primary-400)",
          500: "var(--primary-500)",
          600: "var(--primary-600)",
          700: "var(--primary-700)",
          900: "#000000",
        },
        secondary: {
          50: "var(--secondary-50)",
          300: "var(--secondary-300)",
          400: "var(--secondary-400)",
          500: "var(--secondary-500)",
          600: "var(--secondary-600)",
          700: "var(--secondary-700)",
          900: "#7A0510",
        },
        trust: {
          50: "var(--trust-50)",
          100: "var(--trust-100)",
          500: "var(--trust-500)",
          600: "var(--trust-600)",
          700: "var(--trust-700)",
          muted: "var(--trust-muted)",
        },
        verify: {
          green: "var(--verify-green)",
          "green-bg": "var(--verify-green-bg)",
          red: "var(--verify-red)",
          "red-bg": "var(--verify-red-bg)",
        },
        highlight: {
          yellow: "var(--highlight-yellow)",
          green: "var(--highlight-green)",
          blue: "var(--highlight-blue)",
        },
        "slate-blue": "var(--slate-blue)",
        dark: {
          DEFAULT: "#0D0D0D",
          lighter: "#161616",
          intense: "#0A0A0A",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "Plus Jakarta Sans", "system-ui", "sans-serif"],
        body: ["var(--font-body)", "Plus Jakarta Sans", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px) rotate(0deg)" },
          "50%": { transform: "translateY(-12px) rotate(0.8deg)" },
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(242, 15, 34, 0.4)" },
          "50%": { boxShadow: "0 0 0 20px rgba(242, 15, 34, 0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        float: "float 4s ease-in-out infinite",
        pulseGlow: "pulseGlow 2s ease-out infinite",
        shimmer: "shimmer 3s linear infinite",
        "fade-in": "fade-in 0.4s ease-out forwards",
      },
      boxShadow: {
        "glow-sm": "0 0 20px rgba(242, 15, 34, 0.25)",
        "glow-md": "0 0 40px rgba(242, 15, 34, 0.3)",
        "glow-lg": "0 0 60px rgba(242, 15, 34, 0.4)",
        "glow-blue": "0 0 30px rgba(59, 130, 246, 0.35)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
