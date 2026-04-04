import { useCallback } from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/hooks/useTheme";
import type { ThemePreference } from "@/stores/themeStore";

const options: { value: ThemePreference; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "auto", label: "Auto" },
  { value: "dark", label: "Dark" },
];

interface ThemeToggleProps {
  className?: string;
}

export function ThemeToggle({ className }: ThemeToggleProps) {
  const { preference, setPreference } = useTheme();

  const handleChange = useCallback(
    (pref: ThemePreference) => {
      if (pref === preference) return;
      document.documentElement.classList.add("theme-transition");
      setPreference(pref);
      setTimeout(() => {
        document.documentElement.classList.remove("theme-transition");
      }, 350);
    },
    [preference, setPreference],
  );

  return (
    <div
      className={cn(
        "relative inline-flex rounded-sm border border-border bg-background p-0.5",
        className,
      )}
      role="radiogroup"
      aria-label="Theme preference"
    >
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          role="radio"
          aria-checked={preference === opt.value}
          onClick={() => handleChange(opt.value)}
          className={cn(
            "relative z-10 flex-1 px-3 py-1.5 font-serif text-xs tracking-wide transition-colors cursor-pointer",
            preference === opt.value
              ? "text-accent-foreground"
              : "text-text-muted hover:text-text",
          )}
        >
          {preference === opt.value && (
            <motion.span
              layoutId="theme-indicator"
              className="absolute inset-0 rounded-[1px] bg-accent"
              transition={{ type: "spring", stiffness: 400, damping: 30 }}
            />
          )}
          <span className="relative">{opt.label}</span>
        </button>
      ))}
    </div>
  );
}
