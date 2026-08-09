// @ts-ignore
/* eslint-disable */
import { request, type RequestOptions } from "@/lib/request";

/** 使用邮箱登录 POST /api/auth/login */
export async function loginUser(
  body: API.EmailPasswordRequest,
  options?: RequestOptions
) {
  return request<API.UserResponse>("/api/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}

/** 退出登录 POST /api/auth/logout */
export async function logoutUser(options?: RequestOptions) {
  return request<any>("/api/auth/logout", {
    method: "POST",
    ...(options || {}),
  });
}

/** 查询当前用户 GET /api/auth/me */
export async function getCurrentUser(options?: RequestOptions) {
  return request<API.UserResponse>("/api/auth/me", {
    method: "GET",
    ...(options || {}),
  });
}

/** 刷新登录会话 POST /api/auth/refresh */
export async function refreshUserSession(options?: RequestOptions) {
  return request<API.UserResponse>("/api/auth/refresh", {
    method: "POST",
    ...(options || {}),
  });
}

/** 使用邮箱注册 POST /api/auth/register */
export async function registerUser(
  body: API.RegisterRequest,
  options?: RequestOptions
) {
  return request<API.UserResponse>("/api/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}
