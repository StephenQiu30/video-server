// @ts-ignore
/* eslint-disable */
import { request } from "@umijs/max";

/** Inspect Media Inspect one public video URL and establish an anonymous session. POST /api/v1/media/inspect */
export async function inspectMedia(
  body: API.InspectMediaRequest,
  options?: { [key: string]: any }
) {
  return request<API.InspectedMedia>("/api/v1/media/inspect", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    data: body,
    ...(options || {}),
  });
}
