import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // AgriMesh brand colors
        agri: {
          50: "#f0fdf4",
          100: "#dcfce7",
          200: "#bbf7d0",
          300: "#86efac",
          400: "#4ade80",
          500: "#22c55e",
          600: "#16a34a",
          700: "#15803d",
          800: "#166534",
          900: "#14532d",
        },
        earth: {
          50: "#faf5f0",
          100: "#f5ebe0",
          200: "#e6d5c3",
          300: "#d4b896",
          400: "#c49a6c",
          500: "#b8834f",
          600: "#a66f43",
          700: "#8a5838",
          800: "#714833",
          900: "#5c3c2c",
        },
      },
    },
  },
  plugins: [],
};

export default config;
