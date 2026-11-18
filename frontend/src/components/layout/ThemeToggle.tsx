import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/store/theme";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button onClick={toggle} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`} className="focus-ring glass rounded-xl p-2 hover:shadow-glow">
      {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
