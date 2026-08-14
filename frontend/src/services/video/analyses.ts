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

/** 删除视频分析与报告 隐藏分析任务并异步清理其私有报告对象。 DELETE /api/analyses/${param0} */
export async function deleteAnalysis(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.deleteAnalysisParams,
  options?: RequestOptions
) {
  const { analysis_id: param0, ...queryParams } = params;
  return request<any>(`/api/analyses/${param0}`, {
    method: "DELETE",
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

/** 导出视频分析报告 将已完成的结构化分析结果导出为 DOCX 报告。 GET /api/analyses/${param0}/report.docx */
export async function exportAnalysisReport(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.exportAnalysisReportParams,
  options?: RequestOptions
) {
  const { analysis_id: param0, ...queryParams } = params;
  return request<string>(`/api/analyses/${param0}/report.docx`, {
    method: "GET",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** 导出 Markdown 视频分析报告 导出与前端预览、DOCX 转换共用的唯一 Markdown 报告。 GET /api/analyses/${param0}/report.md */
export async function exportAnalysisMarkdown(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.exportAnalysisMarkdownParams,
  options?: RequestOptions
) {
  const { analysis_id: param0, ...queryParams } = params;
  return request<string>(`/api/analyses/${param0}/report.md`, {
    method: "GET",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** 重试原视频分析任务 为同一分析任务创建下一执行代次，不改变任务资源 ID。

Retry 是上一运行的无参数重放；带请求体的请求按校验错误拒绝。 POST /api/analyses/${param0}/retry */
export async function retryAnalysis(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.retryAnalysisParams,
  options?: RequestOptions
) {
  const { analysis_id: param0, ...queryParams } = params;
  return request<API.AnalysisResponse>(`/api/analyses/${param0}/retry`, {
    method: "POST",
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** 列出输入兼容的分析 Skill 按输入类型返回可选 Skill 及用户可编辑的默认提示词。 GET /api/analysis-skills */
export async function listAnalysisSkills(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.listAnalysisSkillsParams,
  options?: RequestOptions
) {
  return request<API.AnalysisSkillResponse[]>("/api/analysis-skills", {
    method: "GET",
    params: {
      ...params,
    },
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

/** 读取下载任务最近的视频分析 恢复当前用户在该下载任务上最近创建的分析与报告。 GET /api/downloads/${param0}/analysis */
export async function getLatestDownloadAnalysis(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getLatestDownloadAnalysisParams,
  options?: RequestOptions
) {
  const { download_id: param0, ...queryParams } = params;
  return request<API.AnalysisResponse | null>(
    `/api/downloads/${param0}/analysis`,
    {
      method: "GET",
      params: { ...queryParams },
      ...(options || {}),
    }
  );
}
