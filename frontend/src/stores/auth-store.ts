// frontend/src/stores/auth-store.ts
import { create } from 'zustand';

import type { Company, User } from '@/types/api';

interface AuthState {
  user: User | null;
  company: Company | null;
  isHydrated: boolean;
  setSession: (user: User, company: Company) => void;
  clearSession: () => void;
  setHydrated: (value: boolean) => void;
}

/**
 * Holds the current user/company in memory for the session. The JWTs
 * themselves live in localStorage (see lib/token-storage.ts); this store is
 * just for the profile data the UI reads on every page (nav, role guards).
 */
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  company: null,
  isHydrated: false,
  setSession: (user, company) => set({ user, company }),
  clearSession: () => set({ user: null, company: null }),
  setHydrated: (value) => set({ isHydrated: value }),
}));
