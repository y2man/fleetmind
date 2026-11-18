const v = (n) => `rgb(var(--${n}) / <alpha-value>)`;
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: { bg: v("bg"), surface: v("surface"), line: v("line"), ink: v("ink"), muted: v("muted"), electric: v("electric"), violet: v("violet"), ok: v("ok"), warn: v("warn"), danger: v("danger") },
      boxShadow: { glow: "0 0 24px rgb(var(--electric) / 0.35)", card: "0 10px 40px rgb(0 0 0 / 0.25)" },
      keyframes: { shimmer: { "100%": { transform: "translateX(100%)" } } },
      animation: { shimmer: "shimmer 1.6s infinite" },
    },
  },
  plugins: [],
};
