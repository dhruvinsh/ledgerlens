import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import type { PaginatedResponse, ReceiptListItem, Store, StoreAlias } from "@/lib/types";

export function useStores(filters: { search?: string; chain?: string; page?: number; per_page?: number } = {}) {
  return useQuery({
    queryKey: ["stores", filters],
    queryFn: () =>
      api.get<PaginatedResponse<Store>>("/stores", filters as Record<string, string>),
  });
}

export function useStore(id: string | undefined) {
  return useQuery({
    queryKey: ["stores", id],
    queryFn: () => api.get<Store>(`/stores/${id}`),
    enabled: !!id,
  });
}

export function useUpdateStore() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Record<string, unknown>) =>
      api.patch<Store>(`/stores/${id}`, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["stores", vars.id] });
      qc.invalidateQueries({ queryKey: ["stores"] });
    },
  });
}

export function useDeleteStore() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/stores/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["stores"] }),
  });
}

export function useStoreReceipts(
  id: string | undefined,
  page: number = 1,
  per_page: number = 10,
) {
  return useQuery({
    queryKey: ["stores", id, "receipts", page, per_page],
    queryFn: () =>
      api.get<PaginatedResponse<ReceiptListItem>>(`/stores/${id}/receipts`, {
        page: String(page),
        per_page: String(per_page),
      }),
    enabled: !!id,
  });
}

export function useStoreAliases(storeId: string | undefined) {
  return useQuery({
    queryKey: ["stores", storeId, "aliases"],
    queryFn: () => api.get<StoreAlias[]>(`/stores/${storeId}/aliases`),
    enabled: !!storeId,
  });
}

export function useAddStoreAlias() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ storeId, alias_name }: { storeId: string; alias_name: string }) =>
      api.post<StoreAlias>(`/stores/${storeId}/aliases`, { alias_name }),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["stores", vars.storeId, "aliases"] });
      qc.invalidateQueries({ queryKey: ["stores", vars.storeId] });
    },
  });
}

export function useMergeStore() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, duplicate_ids }: { id: string; duplicate_ids: string[] }) =>
      api.post<Store>(`/stores/${id}/merge`, { duplicate_ids }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["stores"] });
      qc.invalidateQueries({ queryKey: ["review-counts"] });
    },
  });
}

export function useRemoveStoreAlias() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ storeId, aliasId }: { storeId: string; aliasId: string }) =>
      api.delete(`/stores/${storeId}/aliases/${aliasId}`),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["stores", vars.storeId, "aliases"] });
      qc.invalidateQueries({ queryKey: ["stores", vars.storeId] });
    },
  });
}
