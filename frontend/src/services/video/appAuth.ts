// @ts-ignore
/* eslint-disable */
import { request, type RequestOptions } from "@/lib/request";

/** 登录原生应用 POST /api/app/v1/auth/login */
export async function loginNativeUser(
  body: API.EmailPasswordRequest,
  options?: RequestOptions
) {
  return request<API.NativeSessionResponse>("/api/app/v1/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}

/** 退出原生应用 POST /api/app/v1/auth/logout */
export async function logoutNativeSession(
  body: API.NativeLogoutRequest,
  options?: RequestOptions
) {
  return request<any>("/api/app/v1/auth/logout", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}

/** 查询原生应用当前用户 GET /api/app/v1/auth/me */
export async function getNativeCurrentUser(options?: RequestOptions) {
  return request<API.UserResponse>("/api/app/v1/auth/me", {
    method: "GET",
    ...(options || {}),
  });
}

/** 轮换原生应用会话 POST /api/app/v1/auth/refresh */
export async function refreshNativeSession(
  body: API.NativeRefreshRequest,
  options?: RequestOptions
) {
  return request<API.NativeSessionResponse>("/api/app/v1/auth/refresh", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}

/** 注册原生应用用户 POST /api/app/v1/auth/register */
export async function registerNativeUser(
  body: API.RegisterRequest,
  options?: RequestOptions
) {
  return request<API.NativeSessionResponse>("/api/app/v1/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}
