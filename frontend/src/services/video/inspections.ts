// @ts-ignore
/* eslint-disable */
import { request, type RequestOptions } from "@/utils/request";

/** 解析媒体信息 校验公开媒体地址并返回可供选择的语义下载格式。 POST /api/inspections */
export async function inspectMedia(
  body: API.InspectionRequest,
  options?: { [key: string]: any }
) {
  return request<API.InspectionResponse>("/api/inspections", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}

/** 查询媒体解析结果 查询当前登录用户拥有的媒体解析结果。 GET /api/inspections/${param0} */
export async function getInspection(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getInspectionParams,
  options?: { [key: string]: any }
) {
  const { inspection_id: param0, ...queryParams } = params;
  return request<API.InspectionResponse>(`/api/inspections/${param0}`, {
    method: "GET",
    params: { ...queryParams },
    ...(options || {}),
  });
}
