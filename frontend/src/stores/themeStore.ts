import { create } from "zustand";

export type ThemePreference = "light" | "dark" | "auto";
export type ResolvedTheme = "light" | "dark";

interface ThemeState {
  preference: ThemePreference;
  resolvedTheme: ResolvedTheme;
  setPreference: (pref: ThemePreference) => void;
  setResolvedTheme: (theme: ResolvedTheme) => void;
}

const STORAGE_KEY = "ledgerlens-theme";

function getSystemTheme(): ResolvedTheme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function getInitialPreference(): ThemePreference {
  if (typeof window === "undefined") return "auto";
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "auto")
      return stored;
  } catch {
    // localStorage unavailable
  }
  return "auto";
}

function resolve(pref: ThemePreference): ResolvedTheme {
  return pref === "auto" ? getSystemTheme() : pref;
}

const initial = getInitialPreference();

export const useThemeStore = create<ThemeState>((set) => ({
  preference: initial,
  resolvedTheme: resolve(initial),

  setPreference: (pref) => {
    try {
      localStorage.setItem(STORAGE_KEY, pref);
    } catch {
      // localStorage unavailable
    }
    set({ preference: pref, resolvedTheme: resolve(pref) });
  },

  setResolvedTheme: (theme) => {
    set({ resolvedTheme: theme });
  },
}));
