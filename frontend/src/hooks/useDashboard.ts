import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";

interface DashboardSummary {
  total_receipts: number;
  total_spent: number;
  total_items: number;
  total_stores: number;
  avg_receipt_total: number;
}

interface SpendingByStore {
  store_id: string;
  store_name: string;
  total: number;
  receipt_count: number;
}

interface SpendingByMonth {
  month: string;
  total: number;
  receipt_count: number;
}

interface SpendingByCategory {
  category: string;
  total: number;
  item_count: number;
}

interface DashboardFilters {
  date_from?: string;
  date_to?: string;
}

export function useDashboardSummary(filters: DashboardFilters = {}) {
  return useQuery({
    queryKey: ["dashboard", "summary", filters],
    queryFn: () =>
      api.get<DashboardSummary>("/dashboard/summary", filters as Record<string, string>),
  });
}

export function useSpendingByStore(filters: DashboardFilters = {}) {
  return useQuery({
    queryKey: ["dashboard", "by-store", filters],
    queryFn: () =>
      api.get<SpendingByStore[]>("/dashboard/spending-by-store", filters as Record<string, string>),
  });
}

export function useSpendingByMonth(filters: DashboardFilters = {}) {
  return useQuery({
    queryKey: ["dashboard", "by-month", filters],
    queryFn: () =>
      api.get<SpendingByMonth[]>("/dashboard/spending-by-month", filters as Record<string, string>),
  });
}

export function useSpendingByCategory(filters: DashboardFilters = {}) {
  return useQuery({
    queryKey: ["dashboard", "by-category", filters],
    queryFn: () =>
      api.get<SpendingByCategory[]>(
        "/dashboard/spending-by-category",
        filters as Record<string, string>,
      ),
  });
}
