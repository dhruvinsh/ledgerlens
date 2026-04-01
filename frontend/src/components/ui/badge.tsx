import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-sm px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "bg-accent/10 text-accent",
        success: "bg-success/10 text-success",
        destructive: "bg-destructive/10 text-destructive",
        warning: "bg-warning/10 text-warning",
        processing: "bg-processing/10 text-processing",
        muted: "bg-border/50 text-text-muted",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant, className }))} {...props} />;
}

export function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; variant: BadgeProps["variant"] }> = {
    pending: { label: "Pending", variant: "warning" },
    processing: { label: "Processing", variant: "processing" },
    processed: { label: "Processed", variant: "success" },
    reviewed: { label: "Reviewed", variant: "success" },
    failed: { label: "Failed", variant: "destructive" },
    deleted: { label: "Deleted", variant: "muted" },
    queued: { label: "Queued", variant: "warning" },
    running: { label: "Running", variant: "processing" },
    completed: { label: "Completed", variant: "success" },
  };
  const c = config[status] ?? { label: status, variant: "muted" as const };
  return <Badge variant={c.variant}>{c.label}</Badge>;
}
