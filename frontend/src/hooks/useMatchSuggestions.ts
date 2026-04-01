import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import type { MatchSuggestion, PaginatedResponse } from "@/lib/types";

export function useSuggestions(page = 1, per_page = 20) {
  return useQuery({
    queryKey: ["suggestions", page, per_page],
    queryFn: () =>
      api.get<PaginatedResponse<MatchSuggestion>>("/suggestions", {
        page: String(page),
        per_page: String(per_page),
      }),
  });
}

export function useAcceptSuggestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<MatchSuggestion>(`/suggestions/${id}/accept`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["suggestions"] });
      qc.invalidateQueries({ queryKey: ["items"] });
    },
  });
}

export function useRejectSuggestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<MatchSuggestion>(`/suggestions/${id}/reject`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["suggestions"] }),
  });
}
