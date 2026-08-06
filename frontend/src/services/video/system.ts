// @ts-ignore
/* eslint-disable */
import { request } from "@umijs/max";

/** Healthz GET /healthz */
export async function healthzHealthzGet(options?: { [key: string]: any }) {
  return request<Record<string, any>>("/healthz", {
    method: "GET",
    ...(options || {}),
  });
}
