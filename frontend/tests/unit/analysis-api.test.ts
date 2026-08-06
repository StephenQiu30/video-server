import { request } from '@umijs/max';
import { describe, expect, it, vi } from 'vitest';

import {
  cancelAnalysis,
  createAnalysis,
  getAnalysis,
} from '@/services/analysis';
import { analysisJob } from './analysis-fixtures';
import { job } from './download-fixtures';

const requestMock = vi.mocked(request);

describe('analysis API', () => {
  it('creates an analysis from a download ID with an idempotency key', async () => {
    requestMock.mockResolvedValue(analysisJob());

    await createAnalysis(
      job().id,
      { profile: 'standard-v1', output_language: 'en-US' },
      'analysis-key',
    );

    expect(requestMock).toHaveBeenCalledWith(
      `/api/downloads/${job().id}/analyses`,
      expect.objectContaining({
        data: {
          profile: 'standard-v1',
          output_language: 'en-US',
        },
        headers: { 'Idempotency-Key': 'analysis-key' },
        method: 'POST',
      }),
    );
  });

  it('queries and cancels by analysis ID without an artifact identifier', async () => {
    const current = analysisJob('running');
    requestMock
      .mockResolvedValueOnce(current)
      .mockResolvedValueOnce(analysisJob('cancelled'));

    await getAnalysis(current.id);
    await cancelAnalysis(current.id);

    expect(requestMock).toHaveBeenNthCalledWith(
      1,
      `/api/analyses/${current.id}`,
      expect.objectContaining({ method: 'GET' }),
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      2,
      `/api/analyses/${current.id}/cancel`,
      expect.objectContaining({ method: 'POST' }),
    );
    expect(JSON.stringify(requestMock.mock.calls)).not.toContain('artifact');
  });
});
