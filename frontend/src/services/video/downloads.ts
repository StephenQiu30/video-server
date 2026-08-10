// @ts-ignore
/* eslint-disable */
import { request, type RequestOptions } from "@/lib/request";

/** 创建下载任务 根据解析结果和语义格式创建异步下载任务。 POST /api/downloads */
export async function createDownload(
  body: API.DownloadRequest,
  options?: RequestOptions
) {
  return request<API.DownloadResponse>("/api/downloads", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}

/** 查询下载任务 查询当前登录用户拥有的下载任务。 GET /api/downloads/${param0} */
export async function getDownload(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getDownloadParams,
  options?: RequestOptions
) {
  const { job_id: param0, ...queryParams } = params;
  return request<API.DownloadResponse>(`/api/downloads/${param0}`, {
    method: "GET",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** 取消下载任务 请求取消尚未结束的下载任务。 POST /api/downloads/${param0}/cancel */
export async function cancelDownload(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.cancelDownloadParams,
  options?: RequestOptions
) {
  const { job_id: param0, ...queryParams } = params;
  return request<API.DownloadResponse>(`/api/downloads/${param0}/cancel`, {
    method: "POST",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** 签发文件下载地址 为已完成的下载任务签发短时制品地址。 POST /api/downloads/${param0}/download-url */
export async function issueDownloadUrl(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.issueDownloadUrlParams,
  options?: RequestOptions
) {
  const { job_id: param0, ...queryParams } = params;
  return request<API.DownloadUrlResponse>(
    `/api/downloads/${param0}/download-url`,
    {
      method: "POST",
      params: { ...queryParams },
      ...(options || {}),
    }
  );
}

/** 重试下载任务 从失败或已取消的任务创建一条新的下载任务。 POST /api/downloads/${param0}/retry */
export async function retryDownload(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.retryDownloadParams,
  options?: RequestOptions
) {
  const { job_id: param0, ...queryParams } = params;
  return request<API.DownloadResponse>(`/api/downloads/${param0}/retry`, {
    method: "POST",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** 查询下载历史 查询当前登录用户的下载历史。 GET /api/downloads/history */
export async function getDownloadHistory(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getDownloadHistoryParams,
  options?: RequestOptions
) {
  return request<API.DownloadHistoryResponse>("/api/downloads/history", {
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
