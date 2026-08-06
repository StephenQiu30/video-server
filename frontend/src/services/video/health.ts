// @ts-ignore
/* eslint-disable */
import { request } from "@umijs/max";

/** Get Liveness GET /health/live */
export async function getLiveness(options?: { [key: string]: any }) {
  return request<Record<string, any>>("/health/live", {
    method: "GET",
    ...(options || {}),
  });
}

/** Get Readiness Return 503 when any configured dependency probe is unavailable. GET /health/ready */
export async function getReadiness(options?: { [key: string]: any }) {
  return request<Record<string, any>>("/health/ready", {
    method: "GET",
    ...(options || {}),
  });
}
