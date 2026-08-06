// @ts-ignore
/* eslint-disable */
import { request } from "@umijs/max";

/** 创建下载任务 根据解析结果和语义格式创建异步下载任务。 POST /api/downloads */
export async function createDownload(
  body: API.DownloadRequest,
  options?: { [key: string]: any }
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

/** 查询下载任务 查询当前匿名会话拥有的下载任务。 GET /api/downloads/${param0} */
export async function getDownload(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getDownloadParams,
  options?: { [key: string]: any }
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
  options?: { [key: string]: any }
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
  options?: { [key: string]: any }
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
