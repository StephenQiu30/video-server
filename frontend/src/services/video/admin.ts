// @ts-ignore
/* eslint-disable */
import { request, type RequestOptions } from "@/utils/request";

/** 查询用户列表 GET /api/admin/users */
export async function listUsers(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.listUsersParams,
  options?: { [key: string]: any }
) {
  return request<API.ManagedUserListResponse>("/api/admin/users", {
    method: "GET",
    params: {
      // page has a default value: 1
      page: "1",
      // page_size has a default value: 20
      page_size: "20",

      ...params,
    },
    ...(options || {}),
  });
}

/** 更新用户角色与账号状态 PATCH /api/admin/users/${param0} */
export async function updateUserAccess(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.updateUserAccessParams,
  body: API.UpdateUserAccessRequest,
  options?: { [key: string]: any }
) {
  const { user_id: param0, ...queryParams } = params;
  return request<API.ManagedUserResponse>(`/api/admin/users/${param0}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    params: { ...queryParams },
    data: body,
    ...(options || {}),
  });
}
