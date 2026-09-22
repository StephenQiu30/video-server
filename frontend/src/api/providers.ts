// @ts-ignore
/* eslint-disable */
import { request, type RequestOptions } from "@/lib/request";

/** 查询平台能力状态 返回不含凭据、出口地址和 Canary 目标的能力快照。 GET /api/providers */
export async function listProviders(options?: RequestOptions) {
  return request<API.ApiResponseProviderListResponse_>("/api/providers", {
    method: "GET",
    ...(options || {}),
  });
}

/** 发起本机平台授权 由本机 Access Agent 使用明确选择的 Chrome 来源完成平台授权。 POST /api/providers/${param0}/authorization */
export async function beginProviderAuthorization(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.beginProviderAuthorizationParams,
  body: API.BeginProviderAuthorizationRequest,
  options?: RequestOptions
) {
  const { provider_key: param0, ...queryParams } = params;
  return request<API.ApiResponseProviderAuthorizationResponse_>(
    `/api/providers/${param0}/authorization`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      params: { ...queryParams },
      data: body,
      ...(options || {}),
    }
  );
}

/** 查询本机平台授权 GET /api/providers/authorization/${param0} */
export async function getProviderAuthorization(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getProviderAuthorizationParams,
  options?: RequestOptions
) {
  const { transaction_id: param0, ...queryParams } = params;
  return request<API.ApiResponseProviderAuthorizationResponse_>(
    `/api/providers/authorization/${param0}`,
    {
      method: "GET",
      params: { ...queryParams },
      ...(options || {}),
    }
  );
}

/** 取消本机平台授权 DELETE /api/providers/authorization/${param0} */
export async function cancelProviderAuthorization(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.cancelProviderAuthorizationParams,
  options?: RequestOptions
) {
  const { transaction_id: param0, ...queryParams } = params;
  return request<any>(`/api/providers/authorization/${param0}`, {
    method: "DELETE",
    params: { ...queryParams },
    ...(options || {}),
  });
}
