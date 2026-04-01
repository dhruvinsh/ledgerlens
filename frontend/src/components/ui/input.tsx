import { cn } from "@/lib/utils";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ className, label, error, id, ...props }: InputProps) {
  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-text">
          {label}
        </label>
      )}
      <input
        id={id}
        className={cn(
          "flex h-9 w-full rounded-sm border border-border bg-surface px-3 py-1 text-sm text-text",
          "placeholder:text-text-muted",
          "focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent",
          "disabled:cursor-not-allowed disabled:opacity-50",
          error && "border-destructive focus:ring-destructive/30",
          className,
        )}
        {...props}
      />
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
