import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import { wsService } from "@/services/websocket";
import type { PaginatedResponse, ProcessingJob } from "@/lib/types";

export function useJobs(page = 1, per_page = 20) {
  return useQuery({
    queryKey: ["jobs", page, per_page],
    queryFn: () =>
      api.get<PaginatedResponse<ProcessingJob>>("/jobs", {
        page: String(page),
        per_page: String(per_page),
      }),
    refetchInterval: 5000, // Poll every 5s for active jobs
  });
}

export function useJobUpdates() {
  const qc = useQueryClient();

  useEffect(() => {
    const unsubscribe = wsService.subscribe(() => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["receipts"] });
    });
    return unsubscribe;
  }, [qc]);
}
