// @ts-ignore
/* eslint-disable */
import { request, type RequestOptions } from "@/lib/request";

/** 发现微信公众号文章中的视频 POST /api/source-discoveries */
export async function createSourceDiscovery(
  body: API.SourceDiscoveryRequest,
  options?: RequestOptions
) {
  return request<API.SourceDiscoveryResponse>("/api/source-discoveries", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}

/** 查询文章视频发现结果 GET /api/source-discoveries/${param0} */
export async function getSourceDiscovery(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getSourceDiscoveryParams,
  options?: RequestOptions
) {
  const { discovery_id: param0, ...queryParams } = params;
  return request<API.SourceDiscoveryResponse>(
    `/api/source-discoveries/${param0}`,
    {
      method: "GET",
      params: { ...queryParams },
      ...(options || {}),
    }
  );
}
