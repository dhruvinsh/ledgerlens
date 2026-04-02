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

function removeFromCache(
  qc: ReturnType<typeof useQueryClient>,
  id: string,
) {
  qc.setQueriesData<PaginatedResponse<MatchSuggestion>>(
    { queryKey: ["suggestions"] },
    (old) => {
      if (!old) return old;
      return {
        ...old,
        items: old.items.filter((s) => s.id !== id),
        total: old.total - 1,
      };
    },
  );
}

export function useAcceptSuggestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<MatchSuggestion>(`/suggestions/${id}/accept`),
    onMutate: (id) => {
      const previous = qc.getQueriesData<PaginatedResponse<MatchSuggestion>>({
        queryKey: ["suggestions"],
      });
      removeFromCache(qc, id);
      return { previous };
    },
    onError: (_err, _id, context) => {
      context?.previous?.forEach(([key, data]) => {
        if (data) qc.setQueryData(key, data);
      });
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["suggestions"] });
      qc.invalidateQueries({ queryKey: ["items"] });
      qc.invalidateQueries({ queryKey: ["review-counts"] });
    },
  });
}

export function useRejectSuggestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<MatchSuggestion>(`/suggestions/${id}/reject`),
    onMutate: (id) => {
      const previous = qc.getQueriesData<PaginatedResponse<MatchSuggestion>>({
        queryKey: ["suggestions"],
      });
      removeFromCache(qc, id);
      return { previous };
    },
    onError: (_err, _id, context) => {
      context?.previous?.forEach(([key, data]) => {
        if (data) qc.setQueryData(key, data);
      });
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["suggestions"] });
      qc.invalidateQueries({ queryKey: ["review-counts"] });
    },
  });
}
