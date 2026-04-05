import { useEffect } from "react";
import { useRouteError, isRouteErrorResponse, useNavigate } from "react-router";
import { AlertTriangle, ArrowLeft, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

function isChunkLoadError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  const msg = error.message.toLowerCase();
  return (
    msg.includes("failed to fetch dynamically imported module") ||
    msg.includes("importing a module script failed") ||
    msg.includes("dynamically imported module")
  );
}

export function RouteError() {
  const error = useRouteError();
  const navigate = useNavigate();

  // After a new build, chunk filenames change. Auto-reload once so the
  // browser picks up the new entry point and chunk hashes.
  useEffect(() => {
    if (!isChunkLoadError(error)) return;
    const reloaded = sessionStorage.getItem("chunk-reload");
    if (!reloaded) {
      sessionStorage.setItem("chunk-reload", "1");
      window.location.reload();
    }
  }, [error]);

  let title = "Something went wrong";
  let message = "An unexpected error occurred.";
  let detail: string | undefined;

  if (isChunkLoadError(error)) {
    title = "App updated";
    message = "A new version was deployed. Reloading…";
  } else if (isRouteErrorResponse(error)) {
    title = `${error.status} ${error.statusText}`;
    message = typeof error.data === "string" ? error.data : "This page couldn't be loaded.";
  } else if (error instanceof Error) {
    message = error.message;
    if (import.meta.env.DEV) {
      detail = error.stack;
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background p-8">
      <div className="w-full max-w-md space-y-6 text-center">
        <div className="flex justify-center">
          <div className="rounded-full bg-destructive/10 p-4">
            <AlertTriangle size={32} className="text-destructive" />
          </div>
        </div>

        <div className="space-y-2">
          <h1 className="font-serif text-2xl text-foreground">{title}</h1>
          <p className="text-sm text-text-muted">{message}</p>
        </div>

        {detail && (
          <pre className="overflow-auto rounded-sm border border-border bg-surface p-4 text-left text-xs text-text-muted">
            {detail}
          </pre>
        )}

        <div className="flex justify-center gap-3">
          <Button variant="outline" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeft size={14} />
            Go back
          </Button>
          <Button size="sm" onClick={() => window.location.reload()}>
            <RefreshCw size={14} />
            Reload
          </Button>
        </div>
      </div>
    </div>
  );
}
