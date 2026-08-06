// @ts-ignore
/* eslint-disable */
import { request } from "@umijs/max";

/** Create Download POST /api/v1/downloads */
export async function createDownloadApiV1DownloadsPost(
  body: API.DownloadRequest,
  options?: { [key: string]: any }
) {
  return request<any>("/api/v1/downloads", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}

/** Get Download GET /api/v1/downloads/${param0} */
export async function getDownloadApiV1DownloadsJobIdGet(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getDownloadApiV1DownloadsJobIdGetParams,
  options?: { [key: string]: any }
) {
  const { job_id: param0, ...queryParams } = params;
  return request<API.DownloadResponse>(`/api/v1/downloads/${param0}`, {
    method: "GET",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Cancel Download POST /api/v1/downloads/${param0}/cancel */
export async function cancelDownloadApiV1DownloadsJobIdCancelPost(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.cancelDownloadApiV1DownloadsJobIdCancelPostParams,
  options?: { [key: string]: any }
) {
  const { job_id: param0, ...queryParams } = params;
  return request<API.DownloadResponse>(`/api/v1/downloads/${param0}/cancel`, {
    method: "POST",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Issue Download Url POST /api/v1/downloads/${param0}/download-url */
export async function issueDownloadUrlApiV1DownloadsJobIdDownloadUrlPost(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.issueDownloadUrlApiV1DownloadsJobIdDownloadUrlPostParams,
  options?: { [key: string]: any }
) {
  const { job_id: param0, ...queryParams } = params;
  return request<API.DownloadUrlResponse>(
    `/api/v1/downloads/${param0}/download-url`,
    {
      method: "POST",
      params: { ...queryParams },
      ...(options || {}),
    }
  );
}
