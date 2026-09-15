/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FAF9F5",
        ink: "#1B2130",
        "ink-soft": "#4A5164",
        brass: "#9C7A2E",
        "brass-light": "#C9A857",
        line: "#DEDAD0",
        risk: {
          high: "#A3312A",
          "high-bg": "#FBEAE8",
          medium: "#966B1F",
          "medium-bg": "#FBF1DE",
          low: "#2F6B4F",
          "low-bg": "#E7F2ED",
        },
      },
      fontFamily: {
        serif: ["'Source Serif 4'", "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
