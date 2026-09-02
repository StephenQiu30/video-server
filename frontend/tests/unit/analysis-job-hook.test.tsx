import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAnalysisJob } from '@/hooks/useAnalysisJob';
import type { CreateAnalysisInput } from '@/types/video';
import { analysisJob } from '../fixtures/analysis-fixtures';
import { stubCryptoUuids } from '../helpers/crypto';

const runtime = vi.hoisted(() => ({
  createAnalysis: vi.fn(),
  deleteAnalysis: vi.fn(),
  getLatestDownloadAnalysis: vi.fn(),
}));

vi.mock('@/services/analysis', () => ({
  cancelAnalysis: vi.fn(),
  createAnalysis: runtime.createAnalysis,
  createDocumentAnalysis: vi.fn(),
  deleteAnalysis: runtime.deleteAnalysis,
  getAnalysis: vi.fn(),
  getLatestDocumentAnalysis: vi.fn(),
  getLatestDownloadAnalysis: runtime.getLatestDownloadAnalysis,
  retryAnalysis: vi.fn(),
}));

describe('useAnalysisJob', () => {
  beforeEach(() => {
    runtime.createAnalysis.mockReset();
    runtime.deleteAnalysis.mockReset();
    runtime.getLatestDownloadAnalysis.mockReset();
    runtime.getLatestDownloadAnalysis.mockResolvedValue(null);
  });

  it('uses a fresh create idempotency key after deleting an analysis', async () => {
    const first = analysisJob('succeeded');
    const second = { ...first, id: '77777777-7777-4777-8777-777777777777' };
    runtime.createAnalysis
      .mockResolvedValueOnce(first)
      .mockResolvedValueOnce(second);
    runtime.deleteAnalysis.mockResolvedValue(undefined);
    stubCryptoUuids(
      '11111111-1111-4111-8111-111111111111',
      '22222222-2222-4222-8222-222222222222',
    );
    const { result } = renderHook(() => useAnalysisJob('download-id', 60_000));
    const input: CreateAnalysisInput = {
      skill_id: 'director-breakdown',
      output_language: 'zh-CN',
      custom_prompt: null,
    };

    await act(async () => result.current.start(input));
    await act(async () => result.current.remove());
    await act(async () => result.current.start(input));

    expect(runtime.createAnalysis).toHaveBeenNthCalledWith(
      1,
      'download-id',
      input,
      '11111111-1111-4111-8111-111111111111',
    );
    expect(runtime.createAnalysis).toHaveBeenNthCalledWith(
      2,
      'download-id',
      input,
      '22222222-2222-4222-8222-222222222222',
    );
  });
});
