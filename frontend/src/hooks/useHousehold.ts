import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";

interface Household {
  id: string;
  name: string;
  owner_id: string;
  sharing_mode: string;
  users: Array<{ id: string; email: string; display_name: string; role: string }>;
  created_at: string;
}

export function useHousehold() {
  return useQuery({
    queryKey: ["household"],
    queryFn: () => api.get<Household>("/household"),
    retry: false,
  });
}

export function useCreateHousehold() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string }) => api.post<Household>("/household", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["household"] }),
  });
}

export function useUpdateHousehold() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.patch<Household>("/household", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["household"] }),
  });
}

export function useCreateInvite() {
  return useMutation({
    mutationFn: () => api.post<{ invite_url: string; token: string }>("/household/invite"),
  });
}

export function useJoinHousehold() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (token: string) => api.post<Household>(`/household/join/${token}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["household"] }),
  });
}

export function useRemoveMember() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (memberId: string) => api.delete(`/household/members/${memberId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["household"] }),
  });
}
