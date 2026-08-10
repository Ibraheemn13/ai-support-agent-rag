import axios, {
  isAxiosError,
  type AxiosError,
  type InternalAxiosRequestConfig,
} from "axios";

import {
  clearSession,
  getAccessToken,
  getRefreshToken,
  setSession,
} from "@/lib/auth/token";
import type { FastAPIErrorBody, FastAPIValidationIssue } from "@/types/api";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL
).replace(/\/+$/, "");

export class APIError extends Error {
  readonly status: number | null;
  readonly details: unknown;

  constructor(message: string, status: number | null = null, details?: unknown) {
    super(message);
    this.name = "APIError";
    this.status = status;
    this.details = details;
    Object.setPrototypeOf(this, APIError.prototype);
  }
}

function formatValidationIssue(issue: FastAPIValidationIssue): string {
  const fieldPath = issue.loc
    .filter((part) => part !== "body")
    .map(String)
    .join(".");

  return fieldPath ? `${fieldPath}: ${issue.msg}` : issue.msg;
}

function messageFromResponseData(data: unknown): string | null {
  if (typeof data === "string" && data.trim()) {
    return data.trim();
  }

  if (!data || typeof data !== "object") {
    return null;
  }

  const errorBody = data as FastAPIErrorBody;
  if (typeof errorBody.detail === "string" && errorBody.detail.trim()) {
    return errorBody.detail.trim();
  }

  if (Array.isArray(errorBody.detail) && errorBody.detail.length > 0) {
    return errorBody.detail.map(formatValidationIssue).join("; ");
  }

  if (typeof errorBody.message === "string" && errorBody.message.trim()) {
    return errorBody.message.trim();
  }

  return null;
}

function fallbackStatusMessage(status: number | null): string {
  switch (status) {
    case 400:
      return "The request could not be completed. Check the provided information.";
    case 401:
      return "Your session has expired. Please sign in again.";
    case 403:
      return "You do not have permission to perform this action.";
    case 404:
      return "The requested resource was not found.";
    case 409:
      return "This action conflicts with the resource's current state.";
    case 413:
      return "The uploaded file is too large.";
    case 415:
      return "This file type is not supported.";
    case 422:
      return "Some provided values are invalid.";
    case 502:
      return "The AI provider could not complete the request. Please try again.";
    default:
      return status && status >= 500
        ? "The server could not complete the request. Please try again."
        : "Something went wrong while contacting the API.";
  }
}

export function normalizeAPIError(error: unknown): APIError {
  if (error instanceof APIError) {
    return error;
  }

  if (isAxiosError(error)) {
    const axiosError = error as AxiosError<unknown>;
    const status = axiosError.response?.status ?? null;
    const responseMessage = messageFromResponseData(axiosError.response?.data);

    if (!axiosError.response && axiosError.code === "ERR_CANCELED") {
      return new APIError("The request was canceled.", null, error);
    }

    if (!axiosError.response) {
      return new APIError(
        "Unable to reach the API. Check that the backend is running and the API base URL is correct.",
        null,
        error,
      );
    }

    return new APIError(
      responseMessage ?? fallbackStatusMessage(status),
      status,
      axiosError.response.data,
    );
  }

  if (error instanceof Error && error.message.trim()) {
    return new APIError(error.message, null, error);
  }

  return new APIError(fallbackStatusMessage(null), null, error);
}

export function isAPIError(error: unknown): error is APIError {
  return error instanceof APIError;
}

export function getAPIErrorMessage(error: unknown): string {
  return normalizeAPIError(error).message;
}

function redirectToLogin(): void {
  if (typeof window === "undefined") {
    return;
  }

  if (window.location.pathname === "/login" || window.location.pathname === "/register") {
    return;
  }

  const returnTo = `${window.location.pathname}${window.location.search}`;
  window.location.assign(`/login?returnTo=${encodeURIComponent(returnTo)}`);
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    Accept: "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const accessToken = getAccessToken();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }

  return config;
});

/**
 * The in-flight refresh, if one is running.
 *
 * A dashboard fires several queries at once, so an expired access token
 * produces several simultaneous 401s. Without this, each would refresh
 * independently — and since refresh tokens rotate and are single-use, the
 * first would succeed and the rest would replay a spent token, which the
 * backend treats as theft and answers by revoking the whole session. The
 * feature would log you out precisely when it was supposed to keep you in.
 *
 * So the first 401 starts the refresh and the others await the same promise.
 */
let refreshInFlight: Promise<string> | null = null;

async function refreshSession(): Promise<string> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new APIError("No refresh token available.", 401);
  }

  // A bare axios call, not `apiClient`: going through the instance would run
  // this same interceptor on failure and recurse.
  const response = await axios.post<{
    access_token: string;
    refresh_token: string;
  }>(`${API_BASE_URL}/api/v1/auth/refresh`, { refresh_token: refreshToken });

  setSession(response.data.access_token, response.data.refresh_token);
  return response.data.access_token;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!isAxiosError(error) || error.response?.status !== 401) {
      return Promise.reject(normalizeAPIError(error));
    }

    const request = error.config as
      | (InternalAxiosRequestConfig & { _retriedAfterRefresh?: boolean })
      | undefined;

    // Only retry once, and never retry the refresh call itself — a 401 from
    // it means the session is genuinely over.
    const isRefreshCall = request?.url?.includes("/auth/refresh");
    if (!request || request._retriedAfterRefresh || isRefreshCall) {
      clearSession();
      redirectToLogin();
      return Promise.reject(normalizeAPIError(error));
    }

    try {
      refreshInFlight = refreshInFlight ?? refreshSession();
      const accessToken = await refreshInFlight;

      request._retriedAfterRefresh = true;
      request.headers.Authorization = `Bearer ${accessToken}`;
      return await apiClient(request);
    } catch {
      clearSession();
      redirectToLogin();
      return Promise.reject(normalizeAPIError(error));
    } finally {
      refreshInFlight = null;
    }
  },
);

export default apiClient;
