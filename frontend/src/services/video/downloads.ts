// @ts-ignore
/* eslint-disable */
import { request } from "@umijs/max";

/** Create Download POST /api/v1/downloads */
export async function createDownload(
  body: API.CreateDownloadRequest,
  options?: { [key: string]: any }
) {
  return request<API.DownloadJob>("/api/v1/downloads", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}

/** Get Download GET /api/v1/downloads/${param0} */
export async function getDownload(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getDownloadParams,
  options?: { [key: string]: any }
) {
  const { job_id: param0, ...queryParams } = params;
  return request<API.DownloadJob>(`/api/v1/downloads/${param0}`, {
    method: "GET",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Create Download Url POST /api/v1/downloads/${param0}/download-url */
export async function createDownloadUrl(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.createDownloadUrlParams,
  options?: { [key: string]: any }
) {
  const { job_id: param0, ...queryParams } = params;
  return request<API.DownloadUrl>(`/api/v1/downloads/${param0}/download-url`, {
    method: "POST",
    params: { ...queryParams },
    ...(options || {}),
  });
}
