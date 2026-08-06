// @ts-ignore
/* eslint-disable */
import { request, type RequestOptions } from "@/shared/api/client";

/** Live Report process liveness without exposing configuration. GET /health/live */
export async function live(options?: RequestOptions) {
  return request<Record<string, any>>("/health/live", {
    method: "GET",
    ...(options || {}),
  });
}

/** Ready Reject traffic when any configured runtime dependency is unavailable. GET /health/ready */
export async function ready(options?: RequestOptions) {
  return request<any>("/health/ready", {
    method: "GET",
    ...(options || {}),
  });
}
