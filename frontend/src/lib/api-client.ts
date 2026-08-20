// frontend/src/lib/api-client.ts
import type { ApiErrorDetail, TokenResponse } from '@/types/api';
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from './token-storage';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

export class ApiClientError extends Error {
  code: string;
  status: number;
  fieldErrors: Record<string, unknown> | null;

  constructor(status: number, detail: ApiErrorDetail) {
    super(detail.message);
    this.name = 'ApiClientError';
    this.code = detail.code;
    this.status = status;
    this.fieldErrors = detail.field_errors;
  }
}

let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    const data: TokenResponse = await res.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  /** Skip attaching the Authorization header (for login/register/refresh). */
  skipAuth?: boolean;
  /** Send as multipart/form-data instead of JSON (for file uploads). */
  isFormData?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, skipAuth, isFormData, headers, ...rest } = options;

  const doFetch = async (): Promise<Response> => {
    const finalHeaders: Record<string, string> = { ...(headers as Record<string, string>) };
    if (!isFormData && body !== undefined) {
      finalHeaders['Content-Type'] = 'application/json';
    }
    if (!skipAuth) {
      const token = getAccessToken();
      if (token) finalHeaders['Authorization'] = `Bearer ${token}`;
    }

    return fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      headers: finalHeaders,
      body: isFormData ? (body as FormData) : body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let res = await doFetch();

  // On 401 (and not already trying to auth), attempt one silent refresh-and-retry.
  if (res.status === 401 && !skipAuth) {
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
    }
    const refreshed = await refreshPromise;
    if (refreshed) {
      res = await doFetch();
    } else {
      clearTokens();
      if (typeof window !== 'undefined') {
        // Locale-agnostic fallback: French is the app default (see spec section 6).
        // A nicer version would preserve the current locale segment; kept simple here.
        const currentLocale = window.location.pathname.split('/')[1] || 'fr';
        window.location.href = `/${currentLocale}/login`;
      }
    }
  }

  if (!res.ok) {
    let detail: ApiErrorDetail = { code: 'unknown_error', message: `Erreur ${res.status}`, field_errors: null };
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      // response wasn't JSON; keep the default detail
    }
    throw new ApiClientError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;

  const contentType = res.headers.get('content-type') ?? '';
  if (contentType.includes('application/json')) {
    return res.json() as Promise<T>;
  }
  return res.blob() as unknown as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string, options?: RequestOptions) => request<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'POST', body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'PATCH', body }),
  delete: <T>(path: string, options?: RequestOptions) => request<T>(path, { ...options, method: 'DELETE' }),
  /** Fetch a binary response (e.g. report download) as a Blob. */
  getBlob: (path: string, options?: RequestOptions) => request<Blob>(path, { ...options, method: 'GET' }),
};
