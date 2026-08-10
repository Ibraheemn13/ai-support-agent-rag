/**
 * Session storage: a short-lived access token and a rotating refresh token.
 *
 * Both live in localStorage. This is a deliberate MVP tradeoff, not an
 * oversight: it matches the backend's bearer-token auth and keeps local setup
 * simple, but it is readable by any script on the page, so an XSS bug becomes
 * a session compromise. The production-grade version is a Secure, HttpOnly,
 * SameSite cookie set by the backend, which requires a server-side session
 * endpoint and CSRF protection. See docs/06-decisions.md (ADR-021, ADR-051).
 *
 * The refresh token is the longer-lived of the two, so it is the more valuable
 * thing to steal. What limits the damage is server-side rotation: it is
 * single-use, and replaying a spent one revokes the whole session family.
 *
 * Writes publish a change event so React can subscribe to token changes rather
 * than reading localStorage once and going stale.
 */

const ACCESS_TOKEN_STORAGE_KEY = "supportmind.access-token";
const REFRESH_TOKEN_STORAGE_KEY = "supportmind.refresh-token";
const TOKEN_CHANGE_EVENT = "supportmind.token-change";

function canUseStorage(): boolean {
  return (
    typeof window !== "undefined" && typeof window.localStorage !== "undefined"
  );
}

function publishChange(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new Event(TOKEN_CHANGE_EVENT));
}

export function getAccessToken(): string | null {
  if (!canUseStorage()) {
    return null;
  }

  return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
}

export function setAccessToken(token: string): void {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
  publishChange();
}

export function clearAccessToken(): void {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  publishChange();
}

export function getRefreshToken(): string | null {
  if (!canUseStorage()) {
    return null;
  }

  return window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
}

/**
 * Store both halves of a session.
 *
 * One function rather than two setters, because the pair is what a session
 * *is* — the refresh endpoint returns a new one of each, and writing one
 * without the other leaves a session that can authenticate but not renew, or
 * renew into an account it is no longer signed into.
 *
 * Only one change event is published, so subscribers see the finished pair
 * rather than an intermediate state.
 */
export function setSession(accessToken: string, refreshToken: string): void {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, refreshToken);
  publishChange();
}

export function clearSession(): void {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
  publishChange();
}

/**
 * Subscribe to token changes, including those made in another browser tab.
 * Shaped for `useSyncExternalStore`.
 */
export function subscribeToAccessToken(callback: () => void): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  window.addEventListener(TOKEN_CHANGE_EVENT, callback);
  window.addEventListener("storage", callback);

  return () => {
    window.removeEventListener(TOKEN_CHANGE_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

export {
  ACCESS_TOKEN_STORAGE_KEY,
  REFRESH_TOKEN_STORAGE_KEY,
  TOKEN_CHANGE_EVENT,
};
