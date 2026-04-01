import { create } from "zustand";
import type { User } from "@/lib/types";
import { api } from "@/services/api";

interface AppState {
  user: User | null;
  loading: boolean;

  // Dashboard filters
  dateFrom: string;
  dateTo: string;
  storeId: string;
  category: string;

  // Actions
  fetchMe: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    displayName: string,
    password: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
  setDashboardFilters: (filters: Partial<DashboardFilters>) => void;
}

interface DashboardFilters {
  dateFrom: string;
  dateTo: string;
  storeId: string;
  category: string;
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  loading: true,
  dateFrom: "",
  dateTo: "",
  storeId: "",
  category: "",

  fetchMe: async () => {
    try {
      const user = await api.get<User>("/auth/me");
      set({ user, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },

  login: async (email, password) => {
    const user = await api.post<User>("/auth/login", { email, password });
    set({ user });
  },

  register: async (email, displayName, password) => {
    const user = await api.post<User>("/auth/register", {
      email,
      display_name: displayName,
      password,
    });
    set({ user });
  },

  logout: async () => {
    await api.post("/auth/logout");
    set({ user: null });
  },

  setDashboardFilters: (filters) =>
    set((state) => ({ ...state, ...filters })),
}));
