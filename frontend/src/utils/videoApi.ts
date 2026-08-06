/**
 * Boundary for the generated Umi OpenAPI client.
 *
 * The response is intentionally `unknown`: response DTOs belong exclusively to
 * `src/services/video/`, which is generated from the server OpenAPI document.
 * The adapter can therefore be wired to the generated operations without
 * copying their types into page code.
 */
export type VideoApiClient = {
  inspect: (body: { url: string }) => Promise<unknown>;
  createDownload: (body: API.CreateDownloadRequest) => Promise<unknown>;
  getDownload: (jobId: string) => Promise<unknown>;
  createDownloadUrl: (jobId: string) => Promise<unknown>;
};

class ApiUnavailableError extends Error {
  readonly status = 503;
  readonly code = 'API_UNAVAILABLE';

  constructor() {
    super('视频服务暂不可用，请稍后重试');
    this.name = 'ApiUnavailableError';
  }
}

type GeneratedServices = {
  inspectMedia: typeof import('@/services/video/media').inspectMedia;
  createDownload: typeof import('@/services/video/downloads').createDownload;
  getDownload: typeof import('@/services/video/downloads').getDownload;
  createDownloadUrl: typeof import('@/services/video/downloads').createDownloadUrl;
};

let generatedServices: Promise<GeneratedServices> | null = null;

async function loadGeneratedServices(): Promise<GeneratedServices> {
  if (!generatedServices) {
    generatedServices = Promise.all([
      import('@/services/video/media'),
      import('@/services/video/downloads'),
    ])
      .then(([media, downloads]) => ({
        inspectMedia: media.inspectMedia,
        createDownload: downloads.createDownload,
        getDownload: downloads.getDownload,
        createDownloadUrl: downloads.createDownloadUrl,
      }))
      .catch(() => {
        throw new ApiUnavailableError();
      });
  }
  return generatedServices;
}

/**
 * All calls are routed through the generated Umi OpenAPI services.  The
 * fail-closed fallback remains useful if a generated service is unavailable
 * during a partial local checkout; it never fabricates a successful response.
 */
export const videoApi: VideoApiClient = {
  inspect: async (body) => {
    const services = await loadGeneratedServices();
    return services.inspectMedia(body, { credentials: 'include' });
  },
  createDownload: async (body) => {
    const services = await loadGeneratedServices();
    return services.createDownload(body, { credentials: 'include' });
  },
  getDownload: async (jobId) => {
    const services = await loadGeneratedServices();
    return services.getDownload({ job_id: jobId }, { credentials: 'include' });
  },
  createDownloadUrl: async (jobId) => {
    const services = await loadGeneratedServices();
    return services.createDownloadUrl(
      { job_id: jobId },
      { credentials: 'include' },
    );
  },
};
