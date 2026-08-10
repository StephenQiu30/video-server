import {
  getCurrentUser as getCurrentUserRequest,
  loginUser as loginUserRequest,
  logoutUser as logoutUserRequest,
  refreshUserSession as refreshUserSessionRequest,
  registerUser as registerUserRequest,
} from '@/services/video/auth';

export type AuthUser = API.UserResponse;
export type EmailCredentials = API.EmailPasswordRequest;
export type RegisterCredentials = API.RegisterRequest;

export function login(credentials: EmailCredentials): Promise<AuthUser> {
  return loginUserRequest(credentials);
}

export function register(credentials: RegisterCredentials): Promise<AuthUser> {
  return registerUserRequest(credentials);
}

export function getCurrentUser(): Promise<AuthUser> {
  return getCurrentUserRequest();
}

export function refreshSession(): Promise<AuthUser> {
  return refreshUserSessionRequest();
}

export function logout(): Promise<void> {
  return logoutUserRequest();
}

export { ApiError, displayError } from '@/lib/request-error';
