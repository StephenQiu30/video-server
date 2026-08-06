// @ts-ignore
/* eslint-disable */
import { request, type RequestOptions } from "@/shared/api/request";

/** Inspect Media POST /api/v1/inspections */
export async function inspectMediaApiV1InspectionsPost(
  body: API.InspectionRequest,
  options?: RequestOptions
) {
  return request<API.InspectionResponse>("/api/v1/inspections", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}

/** Get Inspection GET /api/v1/inspections/${param0} */
export async function getInspectionApiV1InspectionsInspectionIdGet(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getInspectionApiV1InspectionsInspectionIdGetParams,
  options?: RequestOptions
) {
  const { inspection_id: param0, ...queryParams } = params;
  return request<API.InspectionResponse>(`/api/v1/inspections/${param0}`, {
    method: "GET",
    params: { ...queryParams },
    ...(options || {}),
  });
}
