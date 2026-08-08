import { describe, expect, it } from 'vitest';

import {
  cancelAnalysis,
  createAnalysis,
  getAnalysis,
} from '@/services/analysis';
import {
  cancelDownload,
  createDownload,
  getDownload,
  getInspection,
  inspectMedia,
  issueDownloadUrl,
} from '@/services/download';
import { getLiveness, getReadiness } from '@/services/system';
import { httpRequests, mockHttpResponses } from '../helpers/http';
import { analysisJob } from './analysis-fixtures';
import { inspection, job } from './download-fixtures';

describe('typed API client', () => {
  it('uses same-origin download endpoints and idempotency headers', async () => {
    mockHttpResponses(inspection, job());
    await inspectMedia('https://media.example/owned', 'inspect-key');
    await createDownload(
      inspection.id,
      inspection.formats[0].id,
      'download-key',
    );

    expect(httpRequests()).toMatchObject([
      {
        url: '/api/inspections',
        method: 'POST',
        headers: expect.objectContaining({ 'Idempotency-Key': 'inspect-key' }),
      },
      {
        url: '/api/downloads',
        method: 'POST',
        headers: expect.objectContaining({ 'Idempotency-Key': 'download-key' }),
      },
    ]);
    expect(httpRequests()[1]?.data).toEqual({
      inspection_id: inspection.id,
      format_id: inspection.formats[0].id,
    });
  });

  it('covers inspection, download, cancel, file and health endpoints', async () => {
    mockHttpResponses(
      inspection,
      job('running'),
      job('cancelled'),
      {
        url: 'https://objects.example/token',
        expires_at: '2026-08-06T10:05:00Z',
      },
      { status: 'ok' },
      { status: 'ok', service: 'api' },
    );
    await getInspection(inspection.id);
    await getDownload(job().id);
    await cancelDownload(job().id);
    await issueDownloadUrl(job().id);
    await getLiveness();
    await getReadiness();

    expect(httpRequests().map(({ url }) => url)).toEqual([
      `/api/inspections/${inspection.id}`,
      `/api/downloads/${job().id}`,
      `/api/downloads/${job().id}/cancel`,
      `/api/downloads/${job().id}/download-url`,
      '/health/live',
      '/health/ready',
    ]);
  });

  it('creates, queries and cancels analysis resources', async () => {
    mockHttpResponses(
      analysisJob(),
      analysisJob('running'),
      analysisJob('cancelled'),
    );
    await createAnalysis(
      job().id,
      { profile: 'standard-v1', output_language: 'en-US' },
      'analysis-key',
    );
    await getAnalysis(analysisJob().id);
    await cancelAnalysis(analysisJob().id);

    expect(httpRequests()).toMatchObject([
      { url: `/api/downloads/${job().id}/analyses`, method: 'POST' },
      { url: `/api/analyses/${analysisJob().id}`, method: 'GET' },
      { url: `/api/analyses/${analysisJob().id}/cancel`, method: 'POST' },
    ]);
  });
});
