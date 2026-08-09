// @ts-ignore
/* eslint-disable */
import { request, type RequestOptions } from "@/utils/request";

/** 检查进程存活状态 Report process liveness without exposing configuration. GET /health/live */
export async function getLiveness(options?: { [key: string]: any }) {
  return request<API.LivenessResponse>("/health/live", {
    method: "GET",
    ...(options || {}),
  });
}

/** 检查服务就绪状态 Reject traffic when any configured runtime dependency is unavailable. GET /health/ready */
export async function getReadiness(options?: { [key: string]: any }) {
  return request<API.ReadinessResponse>("/health/ready", {
    method: "GET",
    ...(options || {}),
  });
}
