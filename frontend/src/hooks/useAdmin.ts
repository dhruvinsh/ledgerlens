import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import type { ModelConfig } from "@/lib/types";

export function useModels() {
  return useQuery({
    queryKey: ["admin", "models"],
    queryFn: () => api.get<ModelConfig[]>("/admin/models"),
  });
}

export function useCreateModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api.post<ModelConfig>("/admin/models", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "models"] }),
  });
}

export function useUpdateModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Record<string, unknown>) =>
      api.patch<ModelConfig>(`/admin/models/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "models"] }),
  });
}

export function useDeleteModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/admin/models/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "models"] }),
  });
}

export function useTestModel() {
  return useMutation({
    mutationFn: (id: string) =>
      api.post<{ status: string; error?: string }>(`/admin/models/${id}/test`),
  });
}
