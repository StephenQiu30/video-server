// @ts-ignore
/* eslint-disable */
import { request, type RequestOptions } from "@/lib/request";

/** 查询视频分析任务 查询分析进度及经过证据校验的结果。 GET /api/analyses/${param0} */
export async function getAnalysis(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getAnalysisParams,
  options?: RequestOptions
) {
  const { analysis_id: param0, ...queryParams } = params;
  return request<API.AnalysisResponse>(`/api/analyses/${param0}`, {
    method: "GET",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** 取消视频分析任务 请求取消尚未结束的视频分析任务。 POST /api/analyses/${param0}/cancel */
export async function cancelAnalysis(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.cancelAnalysisParams,
  options?: RequestOptions
) {
  const { analysis_id: param0, ...queryParams } = params;
  return request<API.AnalysisResponse>(`/api/analyses/${param0}/cancel`, {
    method: "POST",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** 创建视频分析任务 基于已完成的下载制品创建异步 AI 分析任务。 POST /api/downloads/${param0}/analyses */
export async function createAnalysis(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.createAnalysisParams,
  body: API.AnalysisRequest,
  options?: RequestOptions
) {
  const { download_id: param0, ...queryParams } = params;
  return request<API.AnalysisResponse>(`/api/downloads/${param0}/analyses`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    params: { ...queryParams },
    data: body,
    ...(options || {}),
  });
}
