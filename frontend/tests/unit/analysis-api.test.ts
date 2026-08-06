import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  cancelAnalysis,
  createAnalysis,
  getAnalysis,
} from '@/features/analysis/api';
import { analysisJob } from './analysis-fixtures';
import { job, jsonResponse } from './download-fixtures';

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('analysis API', () => {
  it('creates an analysis from a download ID with an idempotency key', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(analysisJob(), 202));
    vi.stubGlobal('fetch', fetchMock);

    await createAnalysis(
      job().id,
      { profile: 'standard-v1', output_language: 'en-US' },
      'analysis-key',
    );

    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/downloads/${job().id}/analyses`,
      expect.objectContaining({
        credentials: 'same-origin',
        method: 'POST',
        headers: expect.objectContaining({
          'Idempotency-Key': 'analysis-key',
        }),
        body: JSON.stringify({
          profile: 'standard-v1',
          output_language: 'en-US',
        }),
      }),
    );
  });

  it('queries and cancels by analysis ID without an artifact identifier', async () => {
    const current = analysisJob('running');
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(current))
      .mockResolvedValueOnce(jsonResponse(analysisJob('cancelled')));
    vi.stubGlobal('fetch', fetchMock);

    await getAnalysis(current.id);
    await cancelAnalysis(current.id);

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      `/api/v1/analyses/${current.id}`,
      `/api/v1/analyses/${current.id}/cancel`,
    ]);
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'POST' });
    expect(JSON.stringify(fetchMock.mock.calls)).not.toContain('artifact');
  });
});
