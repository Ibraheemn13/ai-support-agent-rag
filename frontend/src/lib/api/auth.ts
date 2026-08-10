import { clearSession, getRefreshToken, setSession } from "@/lib/auth/token";
import type {
  Credentials,
  RegistrationDetails,
  SessionTokens,
  User,
} from "@/types/auth";

import { apiClient } from "./client";

export type RegisterRequest = RegistrationDetails;
export type LoginRequest = Credentials;
export type TokenResponse = SessionTokens;
export type UserResponse = User;

export async function registerUser(data: RegisterRequest): Promise<UserResponse> {
  const response = await apiClient.post<UserResponse>("/api/v1/auth/register", data);
  return response.data;
}

export async function loginUser(data: LoginRequest): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>("/api/v1/auth/login", data);
  setSession(response.data.access_token, response.data.refresh_token);
  return response.data;
}

export async function getCurrentUser(): Promise<UserResponse> {
  const response = await apiClient.get<UserResponse>("/api/v1/auth/me");
  return response.data;
}

/**
 * End the session on the server as well as in this browser.
 *
 * Clearing local storage alone would leave the refresh token valid for its
 * full lifetime — a sign-out that only hides the key. The local clear happens
 * regardless of whether the server call succeeds, because the user asked to be
 * signed out and a network failure must not leave them signed in.
 */
export async function logoutUser(): Promise<void> {
  const refreshToken = getRefreshToken();
  try {
    if (refreshToken) {
      await apiClient.post("/api/v1/auth/logout", {
        refresh_token: refreshToken,
      });
    }
  } catch {
    // Ignored on purpose: see above.
  } finally {
    clearSession();
  }
}

export const authApi = {
  register: registerUser,
  login: loginUser,
  me: getCurrentUser,
  logout: logoutUser,
};
