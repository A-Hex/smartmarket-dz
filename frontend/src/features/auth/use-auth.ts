// frontend/src/features/auth/use-auth.ts
'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import { apiClient } from '@/lib/api-client';
import { clearTokens, getAccessToken, setTokens } from '@/lib/token-storage';
import { useAuthStore } from '@/stores/auth-store';
import type { Company, TokenResponse, User } from '@/types/api';

interface RegisterPayload {
  company_name: string;
  full_name: string;
  email: string;
  password: string;
}

interface LoginPayload {
  email: string;
  password: string;
}

/** Fetches the current user + company and hydrates the auth store. Runs once per session. */
export function useCurrentUser() {
  const setSession = useAuthStore((s) => s.setSession);
  const clearSession = useAuthStore((s) => s.clearSession);
  const setHydrated = useAuthStore((s) => s.setHydrated);

  const query = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      const [user, company] = await Promise.all([
        apiClient.get<User>('/users/me'),
        apiClient.get<Company>('/companies/me'),
      ]);
      return { user, company };
    },
    enabled: typeof window !== 'undefined' && !!getAccessToken(),
    retry: false,
  });

  useEffect(() => {
    if (query.data) {
      setSession(query.data.user, query.data.company);
      setHydrated(true);
    } else if (query.isError) {
      clearSession();
      setHydrated(true);
    } else if (typeof window !== 'undefined' && !getAccessToken()) {
      setHydrated(true);
    }
  }, [query.data, query.isError, setSession, clearSession, setHydrated]);

  return query;
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: LoginPayload) =>
      apiClient.post<TokenResponse>('/auth/login', payload, { skipAuth: true }),
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token);
      queryClient.invalidateQueries({ queryKey: ['me'] });
    },
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RegisterPayload) =>
      apiClient.post<TokenResponse>('/auth/register', payload, { skipAuth: true }),
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token);
      queryClient.invalidateQueries({ queryKey: ['me'] });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const clearSession = useAuthStore((s) => s.clearSession);

  return () => {
    clearTokens();
    clearSession();
    queryClient.clear();
  };
}
