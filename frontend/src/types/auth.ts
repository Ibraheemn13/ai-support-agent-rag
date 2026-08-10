import type { ISODateString, UUID } from "./api";

export interface User {
  id: UUID;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export interface Credentials {
  email: string;
  password: string;
}

export interface RegistrationDetails extends Credentials {
  full_name?: string | null;
}

/** A session: the short-lived bearer token and the token that renews it. */
export interface SessionTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
