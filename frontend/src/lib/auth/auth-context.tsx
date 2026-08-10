"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
} from "react";

import { useIsHydrated } from "@/hooks/use-is-hydrated";

import {
  getCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
  type UserResponse,
} from "@/lib/api/auth";
import { getAccessToken, subscribeToAccessToken } from "@/lib/auth/token";
import { queryKeys } from "@/lib/query-keys";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  user: UserResponse | null;
  status: AuthStatus;
  /** True once a token exists, before the profile has necessarily loaded. */
  hasToken: boolean;
  signIn: (credentials: { email: string; password: string }) => Promise<void>;
  signUp: (data: {
    email: string;
    password: string;
    full_name?: string | null;
  }) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Server render has no localStorage, so it always starts unauthenticated. */
function getTokenSnapshot(): boolean {
  return Boolean(getAccessToken());
}

function getServerTokenSnapshot(): boolean {
  return false;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();

  const hasToken = useSyncExternalStore(
    subscribeToAccessToken,
    getTokenSnapshot,
    getServerTokenSnapshot,
  );

  // The first client render reuses the server snapshot, where no token can
  // exist. Without this, a signed-in user looks signed out for one render,
  // which is long enough for route guards to bounce them to the login page on
  // every reload.
  const hydrated = useIsHydrated();

  const userQuery = useQuery({
    queryKey: queryKeys.currentUser,
    queryFn: getCurrentUser,
    enabled: hasToken,
    // A 401 clears the token via the API client interceptor, so retrying an
    // expired session just delays the redirect to login.
    retry: false,
  });

  const signIn = useCallback(
    async (credentials: { email: string; password: string }) => {
      await loginUser(credentials);
      // The token changed, so any cached data belongs to the previous session.
      // resetQueries rather than clear: clear() removes queries out from under
      // mounted observers, which then never receive the refetch result and sit
      // pending forever. reset discards the same data and refetches in place.
      await queryClient.resetQueries();
    },
    [queryClient],
  );

  const signUp = useCallback(
    async (data: {
      email: string;
      password: string;
      full_name?: string | null;
    }) => {
      // Register returns a user profile rather than a token, so the account has
      // to be exchanged for a session immediately afterwards.
      await registerUser(data);
      await signIn({ email: data.email, password: data.password });
    },
    [signIn],
  );

  const signOut = useCallback(() => {
    // Fire-and-forget: revoking the session server-side is the correct thing to
    // do, but the user should not wait on a network round trip to be signed
    // out, and `logoutUser` clears local storage either way.
    void logoutUser();
    // Same reasoning as signIn: reset keeps observers attached, so signing back
    // in during the same page session still works.
    void queryClient.resetQueries();
    router.replace("/login");
  }, [queryClient, router]);

  const status: AuthStatus = !hydrated
    ? "loading"
    : !hasToken
      ? "unauthenticated"
      : userQuery.isSuccess
        ? "authenticated"
        : userQuery.isError
          ? "unauthenticated"
          : "loading";

  const value = useMemo<AuthContextValue>(
    () => ({
      user: userQuery.data ?? null,
      status,
      hasToken,
      signIn,
      signUp,
      signOut,
    }),
    [hasToken, signIn, signOut, signUp, status, userQuery.data],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return context;
}
