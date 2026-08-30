import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useDocumentImport } from '@/hooks/useDocumentImport';
import { useMediaImport } from '@/hooks/useMediaImport';

const runtime = vi.hoisted(() => ({
  importDocument: vi.fn(),
  importMedia: vi.fn(),
}));

vi.mock('@/services/media-import', () => ({
  cancelLocalVideoImport: vi.fn(),
  displayMediaImportError: () => '上传失败',
  importLocalVideo: runtime.importMedia,
  isMediaImportAbort: (reason: unknown) =>
    reason instanceof DOMException && reason.name === 'AbortError',
  validateLocalVideo: () => null,
}));

vi.mock('@/services/document-import', () => ({
  cancelScreenplayDocumentImport: vi.fn(),
  displayDocumentImportError: () => '上传失败',
  importScreenplayDocument: runtime.importDocument,
  isDocumentImportAbort: (reason: unknown) =>
    reason instanceof DOMException && reason.name === 'AbortError',
  validateScreenplayDocument: () => null,
}));

describe('upload hook cleanup', () => {
  beforeEach(() => {
    runtime.importDocument.mockReset();
    runtime.importMedia.mockReset();
  });

  it('aborts an active media upload when its owner unmounts', async () => {
    let uploadSignal: AbortSignal | undefined;
    runtime.importMedia.mockImplementation(
      async (
        _file: File,
        _key: string,
        _observer: unknown,
        signal: AbortSignal,
      ) => {
        uploadSignal = signal;
        return await aborted(signal);
      },
    );
    const onComplete = vi.fn();
    const { result, unmount } = renderHook(() => useMediaImport(onComplete));

    act(() =>
      result.current.selectFile(
        new File(['video'], 'sample.mp4', { type: 'video/mp4' }),
      ),
    );
    act(() => void result.current.start());
    await waitFor(() => expect(uploadSignal).toBeDefined());

    unmount();
    expect(uploadSignal?.aborted).toBe(true);
    expect(onComplete).not.toHaveBeenCalled();
  });

  it('aborts an active document upload when its owner unmounts', async () => {
    let uploadSignal: AbortSignal | undefined;
    runtime.importDocument.mockImplementation(
      async (
        _file: File,
        _key: string,
        _observer: unknown,
        signal: AbortSignal,
      ) => {
        uploadSignal = signal;
        return await aborted(signal);
      },
    );
    const onComplete = vi.fn();
    const { result, unmount } = renderHook(() => useDocumentImport(onComplete));

    act(() =>
      result.current.selectFile(
        new File(['screenplay'], 'script.txt', { type: 'text/plain' }),
      ),
    );
    act(() => void result.current.start());
    await waitFor(() => expect(uploadSignal).toBeDefined());

    unmount();
    expect(uploadSignal?.aborted).toBe(true);
    expect(onComplete).not.toHaveBeenCalled();
  });
});

function aborted(signal: AbortSignal): Promise<never> {
  return new Promise((_, reject) => {
    signal.addEventListener('abort', () => {
      reject(new DOMException('aborted', 'AbortError'));
    });
  });
}
