import { cn } from "@/lib/utils";

export function Spinner({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center justify-center", className)}>
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-accent" />
    </div>
  );
}
