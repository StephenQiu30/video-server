// @ts-ignore
/* eslint-disable */
import { request, type RequestOptions } from "@/lib/request";

/** 创建本地视频导入 创建只接受 MP4 的浏览器上传资源，不接收任意存储参数。 POST /api/media-imports */
export async function createMediaImport(
  body: API.MediaImportRequest,
  options?: RequestOptions
) {
  return request<API.MediaImportResponse>("/api/media-imports", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}

/** 查询本地视频导入 GET /api/media-imports/${param0} */
export async function getMediaImport(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getMediaImportParams,
  options?: RequestOptions
) {
  const { resource_id: param0, ...queryParams } = params;
  return request<API.MediaImportResponse>(`/api/media-imports/${param0}`, {
    method: "GET",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** 完成视频上传并触发验证 POST /api/media-imports/${param0}/complete */
export async function completeMediaImport(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.completeMediaImportParams,
  body: API.CompleteMediaImportRequest,
  options?: RequestOptions
) {
  const { resource_id: param0, ...queryParams } = params;
  return request<API.MediaImportResponse>(
    `/api/media-imports/${param0}/complete`,
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

/** 创建或刷新视频上传会话 POST /api/media-imports/${param0}/upload-sessions */
export async function createMediaUploadSession(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.createMediaUploadSessionParams,
  options?: RequestOptions
) {
  const { resource_id: param0, ...queryParams } = params;
  return request<API.MediaUploadSessionResponse>(
    `/api/media-imports/${param0}/upload-sessions`,
    {
      method: "POST",
      params: { ...queryParams },
      ...(options || {}),
    }
  );
}
