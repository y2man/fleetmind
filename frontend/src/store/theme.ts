import { create } from "zustand";

type Theme = "dark" | "light";
const KEY = "fleetmind-theme";

function initial(): Theme {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "dark" || saved === "light") return saved;
  } catch { /* storage unavailable */ }
  return "dark";
}
function apply(t: Theme) {
  document.documentElement.classList.toggle("dark", t === "dark");
  try { localStorage.setItem(KEY, t); } catch { /* ignore */ }
}

interface ThemeState { theme: Theme; toggle: () => void }
export const useTheme = create<ThemeState>((set, get) => {
  const t = initial();
  apply(t);
  return { theme: t, toggle: () => { const n = get().theme === "dark" ? "light" : "dark"; apply(n); set({ theme: n }); } };
});
