import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import { useAppStore } from "@/stores/appStore";
import type {
  PaginatedResponse,
  ReviewCounts,
  Store,
  StoreMergeSuggestion,
} from "@/lib/types";

export function useReviewCounts() {
  const user = useAppStore((s) => s.user);
  return useQuery({
    queryKey: ["review-counts"],
    queryFn: () => api.get<ReviewCounts>("/review/counts"),
    enabled: user?.role === "admin",
    refetchInterval: 60_000,
    retry: false,
  });
}

export function useStoreMergeSuggestions(page = 1, per_page = 20) {
  return useQuery({
    queryKey: ["store-merge-suggestions", page, per_page],
    queryFn: () =>
      api.get<PaginatedResponse<StoreMergeSuggestion>>(
        "/stores/merge-suggestions",
        { page: String(page), per_page: String(per_page) },
      ),
  });
}

function removeStoreFromCache(
  qc: ReturnType<typeof useQueryClient>,
  id: string,
) {
  qc.setQueriesData<PaginatedResponse<StoreMergeSuggestion>>(
    { queryKey: ["store-merge-suggestions"] },
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

export function useAcceptStoreMerge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.post<Store>(`/stores/merge-suggestions/${id}/accept`),
    onMutate: (id) => {
      const previous = qc.getQueriesData<PaginatedResponse<StoreMergeSuggestion>>({
        queryKey: ["store-merge-suggestions"],
      });
      removeStoreFromCache(qc, id);
      return { previous };
    },
    onError: (_err, _id, context) => {
      context?.previous?.forEach(([key, data]) => {
        if (data) qc.setQueryData(key, data);
      });
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["store-merge-suggestions"] });
      qc.invalidateQueries({ queryKey: ["review-counts"] });
      qc.invalidateQueries({ queryKey: ["stores"] });
    },
  });
}

export function useRejectStoreMerge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.post(`/stores/merge-suggestions/${id}/reject`),
    onMutate: (id) => {
      const previous = qc.getQueriesData<PaginatedResponse<StoreMergeSuggestion>>({
        queryKey: ["store-merge-suggestions"],
      });
      removeStoreFromCache(qc, id);
      return { previous };
    },
    onError: (_err, _id, context) => {
      context?.previous?.forEach(([key, data]) => {
        if (data) qc.setQueryData(key, data);
      });
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["store-merge-suggestions"] });
      qc.invalidateQueries({ queryKey: ["review-counts"] });
    },
  });
}

export function useScanDuplicates() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ new_suggestions: number }>("/stores/scan-duplicates"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["store-merge-suggestions"] });
      qc.invalidateQueries({ queryKey: ["review-counts"] });
    },
  });
}
