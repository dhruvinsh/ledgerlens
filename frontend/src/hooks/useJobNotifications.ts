import { useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import { useToastStore } from "@/stores/toastStore";
import { useAppStore } from "@/stores/appStore";
import type { PaginatedResponse, ProcessingJob } from "@/lib/types";

/**
 * Polls recent processing jobs and shows toast notifications
 * when a job transitions to completed or failed.
 */
export function useJobNotifications() {
  const prevRef = useRef<Map<string, string>>(new Map());
  const addToast = useToastStore((s) => s.addToast);
  const user = useAppStore((s) => s.user);
  const qc = useQueryClient();

  const { data } = useQuery({
    queryKey: ["jobs", "poll"],
    queryFn: () =>
      api.get<PaginatedResponse<ProcessingJob>>("/jobs", {
        page: "1",
        per_page: "10",
      }),
    refetchInterval: (query) => {
      const jobs = query.state.data?.items ?? [];
      const hasActive = jobs.some(
        (j) => j.status === "queued" || j.status === "running",
      );
      return hasActive ? 3000 : 30000;
    },
    enabled: !!user,
  });

  useEffect(() => {
    if (!data?.items) return;

    const prev = prevRef.current;

    for (const job of data.items) {
      const prevStatus = prev.get(job.id);
      // Only notify on transitions from active → terminal
      if (prevStatus && (prevStatus === "queued" || prevStatus === "running")) {
        if (job.status === "completed") {
          if (job.error_message) {
            // Completed with warning (e.g. LLM failed, used heuristic)
            addToast({
              type: "warning",
              title: "Receipt processed with warnings",
              message: job.error_message,
            });
          } else {
            addToast({
              type: "success",
              title: "Processing complete",
              message: "Your receipt has been processed",
            });
          }
          qc.invalidateQueries({ queryKey: ["receipts"] });
        } else if (job.status === "failed") {
          addToast({
            type: "error",
            title: "Processing failed",
            message: job.error_message || "An error occurred during processing",
          });
          qc.invalidateQueries({ queryKey: ["receipts"] });
        }
      }
    }

    // Update stored states
    const newMap = new Map<string, string>();
    for (const job of data.items) {
      newMap.set(job.id, job.status);
    }
    prevRef.current = newMap;
  }, [data, addToast, qc]);
}
