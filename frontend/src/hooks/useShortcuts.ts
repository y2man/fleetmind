import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { GO_SHORTCUTS } from "@/config/shortcuts";
import { NAV } from "@/config/nav";
import { useAuth } from "@/store/auth";
import { useUi } from "@/store/ui";

const GO_TIMEOUT_MS = 1200;

function isTyping(t: EventTarget | null): boolean {
  const el = t as HTMLElement | null;
  if (!el || !el.tagName) return false;
  return el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName);
}

/**
 * Global keyboard shortcuts. They never fire while typing in a field or while a dialog is open,
 * so they cannot swallow normal text input or act on the page behind a modal.
 * Ctrl/Cmd+K is the one exception: it works from fields too and toggles the palette.
 */
export function useShortcuts() {
  const navigate = useNavigate();

  useEffect(() => {
    let waitingForSecondKey = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const clear = () => { waitingForSecondKey = false; if (timer) clearTimeout(timer); };

    const onKey = (e: KeyboardEvent) => {
      const ui = useUi.getState();
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (ui.paletteOpen) ui.setPalette(false);
        else if (!document.querySelector('[role="dialog"][aria-modal="true"]')) ui.setPalette(true);
        return;
      }
      if (e.ctrlKey || e.metaKey || e.altKey || e.defaultPrevented || e.repeat) return;
      if (isTyping(e.target) || ui.paletteOpen || ui.helpOpen || document.querySelector('[role="dialog"][aria-modal="true"]')) { clear(); return; }

      if (waitingForSecondKey) {
        clear();
        const target = GO_SHORTCUTS.find((s) => s.key === e.key.toLowerCase());
        const item = target && NAV.find((n) => n.to === target.to);
        if (target && item && (!item.permission || useAuth.getState().can(item.permission))) { e.preventDefault(); navigate(target.to); }
        return;
      }
      if (e.key === "g") { waitingForSecondKey = true; timer = setTimeout(clear, GO_TIMEOUT_MS); return; }
      if (e.key === "?") { e.preventDefault(); ui.setHelp(true); return; }
      if (e.key === "/") { e.preventDefault(); ui.setPalette(true); }
    };

    window.addEventListener("keydown", onKey);
    return () => { window.removeEventListener("keydown", onKey); clear(); };
  }, [navigate]);
}
