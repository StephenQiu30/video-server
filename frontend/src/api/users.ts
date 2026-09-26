// @ts-ignore
/* eslint-disable */
import { request, type RequestOptions } from "@/lib/request";

/** 更新当前用户资料 PATCH /api/users/me */
export async function updateCurrentUser(
  body: API.UpdateProfileRequest,
  options?: RequestOptions
) {
  return request<API.ApiResponseUserResponse_>("/api/users/me", {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}

/** 读取当前用户头像 GET /api/users/me/avatar */
export async function getCurrentUserAvatar(options?: RequestOptions) {
  return request<any>("/api/users/me/avatar", {
    method: "GET",
    ...(options || {}),
  });
}

/** 上传当前用户头像 PUT /api/users/me/avatar */
export async function uploadCurrentUserAvatar(
  body: Blob,
  options?: RequestOptions
) {
  return request<API.ApiResponseUserResponse_>("/api/users/me/avatar", {
    method: "PUT",
    headers: {
      "Content-Type": "application/octet-stream",
    },
    data: body,
    ...(options || {}),
  });
}

/** 移除当前用户头像 DELETE /api/users/me/avatar */
export async function deleteCurrentUserAvatar(options?: RequestOptions) {
  return request<API.ApiResponseUserResponse_>("/api/users/me/avatar", {
    method: "DELETE",
    ...(options || {}),
  });
}
