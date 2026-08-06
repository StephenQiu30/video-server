// @ts-ignore
/* eslint-disable */
import { request } from "@umijs/max";

/** Get Analysis GET /api/v1/analyses/${param0} */
export async function getAnalysisApiV1AnalysesAnalysisIdGet(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getAnalysisApiV1AnalysesAnalysisIdGetParams,
  options?: { [key: string]: any }
) {
  const { analysis_id: param0, ...queryParams } = params;
  return request<API.AnalysisResponse>(`/api/v1/analyses/${param0}`, {
    method: "GET",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Cancel Analysis POST /api/v1/analyses/${param0}/cancel */
export async function cancelAnalysisApiV1AnalysesAnalysisIdCancelPost(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.cancelAnalysisApiV1AnalysesAnalysisIdCancelPostParams,
  options?: { [key: string]: any }
) {
  const { analysis_id: param0, ...queryParams } = params;
  return request<API.AnalysisResponse>(`/api/v1/analyses/${param0}/cancel`, {
    method: "POST",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Create Analysis POST /api/v1/downloads/${param0}/analyses */
export async function createAnalysisApiV1DownloadsDownloadIdAnalysesPost(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.createAnalysisApiV1DownloadsDownloadIdAnalysesPostParams,
  body: API.AnalysisRequest,
  options?: { [key: string]: any }
) {
  const { download_id: param0, ...queryParams } = params;
  return request<any>(`/api/v1/downloads/${param0}/analyses`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    params: { ...queryParams },
    data: body,
    ...(options || {}),
  });
}
