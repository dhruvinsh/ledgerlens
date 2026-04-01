import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import type { CanonicalItem, PaginatedResponse, PricePoint } from "@/lib/types";

export function useItems(filters: { search?: string; page?: number; per_page?: number } = {}) {
  return useQuery({
    queryKey: ["items", filters],
    queryFn: () =>
      api.get<PaginatedResponse<CanonicalItem>>("/items", filters as Record<string, string>),
  });
}

export function useItem(id: string | undefined) {
  return useQuery({
    queryKey: ["items", id],
    queryFn: () => api.get<CanonicalItem>(`/items/${id}`),
    enabled: !!id,
  });
}

export function useItemPrices(
  id: string | undefined,
  params?: { store_ids?: string; date_from?: string; date_to?: string },
) {
  return useQuery({
    queryKey: ["items", id, "prices", params],
    queryFn: () =>
      api.get<{ item: CanonicalItem; data_points: PricePoint[] }>(
        `/items/${id}/prices`,
        params as Record<string, string>,
      ),
    enabled: !!id,
  });
}

export function useUpdateItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Record<string, unknown>) =>
      api.patch<CanonicalItem>(`/items/${id}`, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["items", vars.id] });
      qc.invalidateQueries({ queryKey: ["items"] });
    },
  });
}

export function useDeleteItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/items/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["items"] }),
  });
}

export function useUploadItemImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, formData }: { id: string; formData: FormData }) =>
      api.upload<CanonicalItem>(`/items/${id}/image`, formData),
    onSuccess: (_, vars) => qc.invalidateQueries({ queryKey: ["items", vars.id] }),
  });
}

export function useDeleteItemImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<CanonicalItem>(`/items/${id}/image`),
    onSuccess: (_, id) => qc.invalidateQueries({ queryKey: ["items", id] }),
  });
}

export function useFetchItemImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post(`/items/${id}/fetch-image`),
    onSuccess: (_, id) => qc.invalidateQueries({ queryKey: ["items", id] }),
  });
}
