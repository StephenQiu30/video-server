import { describe, expect, it } from 'vitest';

import {
  cancelAnalysis,
  createAnalysis,
  getAnalysis,
} from '@/services/analysis';
import {
  getCurrentUser,
  login,
  logout,
  refreshSession,
  register,
} from '@/services/auth';
import {
  cancelDownload,
  createDownload,
  getDownload,
  getInspection,
  inspectMedia,
  issueDownloadUrl,
} from '@/services/download';
import { getLiveness, getReadiness } from '@/services/system';
import { analysisJob } from '../fixtures/analysis-fixtures';
import { inspection, job } from '../fixtures/download-fixtures';
import { httpRequests, mockHttpResponses } from '../helpers/http';

describe('typed API client', () => {
  it('covers email registration, JWT session restore and logout endpoints', async () => {
    const user = {
      id: '11111111-1111-4111-8111-111111111111',
      email: 'user@example.com',
      created_at: '2026-08-09T10:00:00Z',
    };
    mockHttpResponses(user, user, user, user, undefined);

    await register({ email: user.email, password: 'strong-pass-123' });
    await login({ email: user.email, password: 'strong-pass-123' });
    await getCurrentUser();
    await refreshSession();
    await logout();

    expect(httpRequests().map(({ url }) => url)).toEqual([
      '/api/auth/register',
      '/api/auth/login',
      '/api/auth/me',
      '/api/auth/refresh',
      '/api/auth/logout',
    ]);
  });

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
