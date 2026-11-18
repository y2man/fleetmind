/** "g" then a key jumps to a page. The help dialog and the key handler both read this one list. */
export const GO_SHORTCUTS: { key: string; to: string }[] = [
  { key: "d", to: "/app/dashboard" },
  { key: "f", to: "/app/fleet" },
  { key: "r", to: "/app/drivers" },
  { key: "e", to: "/app/deliveries" },
  { key: "l", to: "/app/tracking" },
  { key: "o", to: "/app/routes" },
  { key: "u", to: "/app/fuel" },
  { key: "m", to: "/app/maintenance" },
  { key: "a", to: "/app/analytics" },
  { key: "i", to: "/app/ai" },
  { key: "n", to: "/app/notifications" },
];

export const GENERAL_SHORTCUTS: { keys: string; label: string }[] = [
  { keys: "Ctrl/⌘ + K", label: "Open the command palette (search and commands)" },
  { keys: "/", label: "Open the command palette" },
  { keys: "?", label: "Show this list" },
  { keys: "Esc", label: "Close a dialog or palette" },
];
