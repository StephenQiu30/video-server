// @ts-ignore
/* eslint-disable */
import { request, type RequestOptions } from "@/lib/request";

/** 查询 AI 分析 Provider GET /api/admin/ai-providers */
export async function listAiProviderProfiles(options?: RequestOptions) {
  return request<API.ApiResponseAiProviderProfileListResponse_>(
    "/api/admin/ai-providers",
    {
      method: "GET",
      ...(options || {}),
    }
  );
}

/** 新增 AI 分析 Provider POST /api/admin/ai-providers */
export async function createAiProviderProfile(
  body: API.CreateAiProviderProfileRequest,
  options?: RequestOptions
) {
  return request<API.ApiResponseAiProviderProfileResponse_>(
    "/api/admin/ai-providers",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      data: body,
      ...(options || {}),
    }
  );
}

/** 删除 AI 分析 Provider DELETE /api/admin/ai-providers/${param0} */
export async function deleteAiProviderProfile(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.deleteAiProviderProfileParams,
  options?: RequestOptions
) {
  const { provider_key: param0, ...queryParams } = params;
  return request<any>(`/api/admin/ai-providers/${param0}`, {
    method: "DELETE",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** 更新 AI 分析 Provider PATCH /api/admin/ai-providers/${param0} */
export async function updateAiProviderProfile(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.updateAiProviderProfileParams,
  body: API.UpdateAiProviderProfileRequest,
  options?: RequestOptions
) {
  const { provider_key: param0, ...queryParams } = params;
  return request<API.ApiResponseAiProviderProfileResponse_>(
    `/api/admin/ai-providers/${param0}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      params: { ...queryParams },
      data: body,
      ...(options || {}),
    }
  );
}

/** 启用 AI 分析 Provider POST /api/admin/ai-providers/${param0}/activate */
export async function activateAiProviderProfile(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.activateAiProviderProfileParams,
  options?: RequestOptions
) {
  const { provider_key: param0, ...queryParams } = params;
  return request<API.ApiResponseAiProviderProfileResponse_>(
    `/api/admin/ai-providers/${param0}/activate`,
    {
      method: "POST",
      params: { ...queryParams },
      ...(options || {}),
    }
  );
}

/** 查询 OpenRouter 公开模型能力 GET /api/admin/ai-providers/models/openrouter */
export async function listOpenRouterModels(options?: RequestOptions) {
  return request<API.ApiResponseAiModelListResponse_>(
    "/api/admin/ai-providers/models/openrouter",
    {
      method: "GET",
      ...(options || {}),
    }
  );
}

/** 查询下载分析 按 UTC 自然日查询管理员可见的全局下载聚合。 GET /api/admin/downloads/analytics */
export async function getDownloadAnalytics(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getDownloadAnalyticsParams,
  options?: RequestOptions
) {
  return request<API.ApiResponseDownloadAnalyticsResponse_>(
    "/api/admin/downloads/analytics",
    {
      method: "GET",
      params: {
        // days has a default value: 30
        days: "30",
        ...params,
      },
      ...(options || {}),
    }
  );
}

/** 分页查询持久文件 GET /api/admin/files */
export async function listStoredFiles(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.listStoredFilesParams,
  options?: RequestOptions
) {
  return request<API.ApiResponseStoredFileListResponse_>("/api/admin/files", {
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

/** 手动清理指定天数前的文件 POST /api/admin/files/cleanup */
export async function cleanupStoredFiles(
  body: API.StorageCleanupRequest,
  options?: RequestOptions
) {
  return request<API.ApiResponseStorageCleanupResponse_>(
    "/api/admin/files/cleanup",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      data: body,
      ...(options || {}),
    }
  );
}

/** 读取已开放平台的脱敏运行诊断 仅元数据快照，不登录、不导出会话、不解析或下载媒体。 GET /api/admin/provider-runtime */
export async function getAdminProviderRuntime(options?: RequestOptions) {
  return request<API.ApiResponseProviderRuntimeListResponse_>(
    "/api/admin/provider-runtime",
    {
      method: "GET",
      ...(options || {}),
    }
  );
}

/** 查询平台目录 GET /api/admin/providers */
export async function listProviderCatalogEntries(options?: RequestOptions) {
  return request<API.ApiResponseProviderCatalogListResponse_>(
    "/api/admin/providers",
    {
      method: "GET",
      ...(options || {}),
    }
  );
}

/** 新增平台目录条目 POST /api/admin/providers */
export async function createProviderCatalogEntry(
  body: API.CreateProviderCatalogEntryRequest,
  options?: RequestOptions
) {
  return request<API.ApiResponseProviderCatalogEntryResponse_>(
    "/api/admin/providers",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      data: body,
      ...(options || {}),
    }
  );
}

/** 删除平台目录条目 DELETE /api/admin/providers/${param0} */
export async function deleteProviderCatalogEntry(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.deleteProviderCatalogEntryParams,
  options?: RequestOptions
) {
  const { provider_key: param0, ...queryParams } = params;
  return request<any>(`/api/admin/providers/${param0}`, {
    method: "DELETE",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** 更新平台目录条目 PATCH /api/admin/providers/${param0} */
export async function updateProviderCatalogEntry(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.updateProviderCatalogEntryParams,
  body: API.UpdateProviderCatalogEntryRequest,
  options?: RequestOptions
) {
  const { provider_key: param0, ...queryParams } = params;
  return request<API.ApiResponseProviderCatalogEntryResponse_>(
    `/api/admin/providers/${param0}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      params: { ...queryParams },
      data: body,
      ...(options || {}),
    }
  );
}

/** 查询用户列表 GET /api/admin/users */
export async function listUsers(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.listUsersParams,
  options?: RequestOptions
) {
  return request<API.ApiResponseManagedUserListResponse_>("/api/admin/users", {
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
  options?: RequestOptions
) {
  const { user_id: param0, ...queryParams } = params;
  return request<API.ApiResponseManagedUserResponse_>(
    `/api/admin/users/${param0}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      params: { ...queryParams },
      data: body,
      ...(options || {}),
    }
  );
}
