import { create } from "zustand";

interface UiState {
  paletteOpen: boolean;
  helpOpen: boolean;
  setPalette: (open: boolean) => void;
  setHelp: (open: boolean) => void;
}

/** Overlays opened by the keyboard shortcuts (command palette, shortcut help). */
export const useUi = create<UiState>((set) => ({
  paletteOpen: false,
  helpOpen: false,
  setPalette: (paletteOpen) => set({ paletteOpen, helpOpen: false }),
  setHelp: (helpOpen) => set({ helpOpen, paletteOpen: false }),
}));
