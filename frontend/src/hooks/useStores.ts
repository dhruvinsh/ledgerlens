import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import type { PaginatedResponse, Store } from "@/lib/types";

export function useStores(filters: { search?: string; page?: number; per_page?: number } = {}) {
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
