import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import type { PaginatedResponse, Receipt } from "@/lib/types";

interface ReceiptFilters {
  status?: string;
  store_id?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_dir?: string;
  page?: number;
  per_page?: number;
}

export function useReceipts(filters: ReceiptFilters = {}) {
  return useQuery({
    queryKey: ["receipts", filters],
    queryFn: () =>
      api.get<PaginatedResponse<Receipt>>("/receipts", filters as Record<string, string>),
  });
}

export function useReceipt(id: string | undefined) {
  return useQuery({
    queryKey: ["receipts", id],
    queryFn: () => api.get<Receipt>(`/receipts/${id}`),
    enabled: !!id,
  });
}

export function useUploadReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => api.upload<Receipt>("/receipts", formData),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["receipts"] }),
  });
}

export function useManualReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api.post<Receipt>("/receipts/manual", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["receipts"] }),
  });
}

export function useUpdateReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Record<string, unknown>) =>
      api.patch<Receipt>(`/receipts/${id}`, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["receipts", vars.id] });
      qc.invalidateQueries({ queryKey: ["receipts"] });
    },
  });
}

export function useDeleteReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/receipts/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["receipts"] }),
  });
}

export function useReprocessReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post(`/receipts/${id}/reprocess`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["receipts"] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}
