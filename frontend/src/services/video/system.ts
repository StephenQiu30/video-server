// @ts-ignore
/* eslint-disable */
import { request } from "@umijs/max";

/** Live Report process liveness without exposing configuration. GET /health/live */
export async function liveHealthLiveGet(options?: { [key: string]: any }) {
  return request<Record<string, any>>("/health/live", {
    method: "GET",
    ...(options || {}),
  });
}

/** Ready Reject traffic when any configured runtime dependency is unavailable. GET /health/ready */
export async function readyHealthReadyGet(options?: { [key: string]: any }) {
  return request<any>("/health/ready", {
    method: "GET",
    ...(options || {}),
  });
}
