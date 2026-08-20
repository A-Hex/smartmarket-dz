// frontend/src/lib/token-storage.ts
// Thin wrapper around localStorage for JWT storage. Guarded for SSR (no window).
// This is a real browser app (not a claude.ai artifact), so localStorage is the
// correct persistence choice here, unlike in the Artifacts sandbox.

const ACCESS_TOKEN_KEY = 'smartmarket_access_token';
const REFRESH_TOKEN_KEY = 'smartmarket_refresh_token';

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}
