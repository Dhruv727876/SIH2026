import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-noto-sans)", "Noto Sans", "-apple-system", "sans-serif"],
        serif: ["var(--font-noto-serif)", "Noto Serif", "Georgia", "serif"],
        mono: ["var(--font-jetbrains-mono)", "JetBrains Mono", "monospace"],
        inter: ["var(--font-inter)", "Inter", "sans-serif"],
      },
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        border: "var(--border)",
        gov: {
          navy: "#001f3f",
          primary: "#12355b",
          dark: "#0b2545",
          accent: "#1e3a8a",
          saffron: "#e65100",
          saffronLight: "#fff9c4",
          green: "#15803d",
          greenLight: "#e8f5e9",
          slate: "#f8f9ff",
          surface: "#f8f9ff",
          border: "#cbd5e1",
          borderLight: "#e2e8f0",
          card: "#ffffff",
          muted: "#475569",
        },
        primary: {
          DEFAULT: "#12355b",
          dark: "#001f3f",
          container: "#12355b",
          light: "#d3e3ff",
        },
        surface: {
          DEFAULT: "#f8f9ff",
          container: "#e6eeff",
          "container-low": "#eff4ff",
          "container-high": "#dce9ff",
          "container-highest": "#d5e3fc",
          "container-lowest": "#ffffff",
        },
      },
    },
  },
  plugins: [],
};
export default config;
