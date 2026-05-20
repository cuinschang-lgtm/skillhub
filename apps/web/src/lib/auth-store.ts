"use client";

import { create } from "zustand";

export type AuthUser = {
  email: string;
  role: "teacher" | "student";
  displayName: string;
};

type AuthState = {
  user: AuthUser | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: true,
  refresh: async () => {
    set({ loading: true });
    try {
      const res = await fetch("/api/auth/me", { credentials: "include" });
      if (!res.ok) {
        set({ user: null, loading: false });
        return;
      }
      const data = (await res.json()) as { user: AuthUser | null };
      set({ user: data.user, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },
  logout: async () => {
    try {
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    } finally {
      set({ user: null });
    }
  },
}));

