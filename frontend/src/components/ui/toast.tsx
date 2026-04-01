import { motion, AnimatePresence } from "motion/react";
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from "lucide-react";
import { useToastStore, type Toast } from "@/stores/toastStore";

const icons = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const styles = {
  success: "border-success/30 bg-success/5",
  error: "border-destructive/30 bg-destructive/5",
  warning: "border-warning/30 bg-warning/5",
  info: "border-processing/30 bg-processing/5",
};

const iconColors = {
  success: "text-success",
  error: "text-destructive",
  warning: "text-warning",
  info: "text-processing",
};

function ToastItem({ toast }: { toast: Toast }) {
  const { removeToast } = useToastStore();
  const Icon = icons[toast.type];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: 80, scale: 0.95 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
      className={`flex items-start gap-3 rounded-sm border bg-surface px-4 py-3 shadow-lg ${styles[toast.type]}`}
    >
      <Icon size={18} className={`mt-0.5 shrink-0 ${iconColors[toast.type]}`} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium">{toast.title}</p>
        {toast.message && (
          <p className="mt-0.5 text-xs text-text-muted">{toast.message}</p>
        )}
      </div>
      <button
        onClick={() => removeToast(toast.id)}
        className="shrink-0 text-text-muted transition-colors hover:text-text"
      >
        <X size={14} />
      </button>
    </motion.div>
  );
}

export function ToastContainer() {
  const { toasts } = useToastStore();

  return (
    <div className="pointer-events-none fixed inset-x-0 top-4 z-[100] flex justify-center">
      <div className="pointer-events-auto flex w-96 max-w-[calc(100vw-2rem)] flex-col gap-2">
        <AnimatePresence mode="popLayout">
          {toasts.map((toast) => (
            <ToastItem key={toast.id} toast={toast} />
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
