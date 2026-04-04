import { useEffect } from "react";
import { useThemeStore } from "@/stores/themeStore";

const THEME_COLORS = {
  light: "#fafaf7",
  dark: "#1a1816",
} as const;

export function useTheme() {
  const { preference, resolvedTheme, setPreference, setResolvedTheme } =
    useThemeStore();

  // Apply .dark class and update <meta theme-color> on resolved theme change
  useEffect(() => {
    const root = document.documentElement;
    if (resolvedTheme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }

    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute("content", THEME_COLORS[resolvedTheme]);
    }
  }, [resolvedTheme]);

  // Listen for system theme changes when preference is "auto"
  useEffect(() => {
    if (preference !== "auto") return;

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => {
      setResolvedTheme(e.matches ? "dark" : "light");
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [preference, setResolvedTheme]);

  return {
    preference,
    resolvedTheme,
    setPreference,
    isDark: resolvedTheme === "dark",
  };
}
