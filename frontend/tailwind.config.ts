import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      backgroundImage: {
        paper:
          "linear-gradient(180deg, rgba(255,255,255,0.45), rgba(255,255,255,0)), linear-gradient(90deg, rgba(15,118,110,0.06) 1px, transparent 1px), linear-gradient(rgba(154,52,18,0.04) 1px, transparent 1px)",
      },
      backgroundSize: {
        paper: "100% 100%, 28px 28px, 28px 28px",
      },
      boxShadow: {
        soft: "0 12px 40px rgba(21, 35, 45, 0.08)",
      },
      borderRadius: {
        card: "20px",
        pill: "999px",
      },
      colors: {
        app: "var(--bg-app)",
        surface: "var(--bg-surface)",
        elevated: "var(--bg-elevated)",
        strong: "var(--fg-strong)",
        muted: "var(--fg-muted)",
        subtle: "var(--line-subtle)",
        primary: "var(--accent-primary)",
        secondary: "var(--accent-secondary)",
        success: "var(--state-success)",
        warning: "var(--state-warning)",
        danger: "var(--state-danger)",
        info: "var(--state-info)",
      },
      fontFamily: {
        sans: ["var(--font-ui)", "IBM Plex Sans", "Helvetica Neue", "sans-serif"],
        serif: ["var(--font-display)", "Newsreader", "Georgia", "serif"],
        mono: ["var(--font-mono)", "IBM Plex Mono", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
