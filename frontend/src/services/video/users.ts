// @ts-ignore
/* eslint-disable */
import { request, type RequestOptions } from "@/utils/request";

/** 更新当前用户资料 PATCH /api/users/me */
export async function updateCurrentUser(
  body: API.UpdateProfileRequest,
  options?: { [key: string]: any }
) {
  return request<API.UserResponse>("/api/users/me", {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}
