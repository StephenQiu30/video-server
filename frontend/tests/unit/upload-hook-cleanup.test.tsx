import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useDocumentImport } from '@/hooks/useDocumentImport';
import { useMediaImport } from '@/hooks/useMediaImport';

const runtime = vi.hoisted(() => ({
  cancelDocument: vi.fn(),
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
  cancelScreenplayDocumentImport: runtime.cancelDocument,
  displayDocumentImportError: () => '上传失败',
  importScreenplayDocument: runtime.importDocument,
  isDocumentImportAbort: (reason: unknown) =>
    reason instanceof DOMException && reason.name === 'AbortError',
  validateScreenplayDocument: () => null,
}));

describe('upload hook cleanup', () => {
  beforeEach(() => {
    runtime.cancelDocument.mockReset();
    runtime.cancelDocument.mockResolvedValue(undefined);
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

  it('cleans a created document resource after upload failure', async () => {
    runtime.importDocument.mockImplementation(
      async (_file, _key, observer: { onResource: (id: string) => void }) => {
        observer.onResource('failed-document');
        throw new Error('storage unavailable');
      },
    );
    const { result } = renderHook(() => useDocumentImport(vi.fn()));

    act(() =>
      result.current.selectFile(
        new File(['screenplay'], 'script.txt', { type: 'text/plain' }),
      ),
    );
    act(() => void result.current.start());

    await waitFor(() =>
      expect(runtime.cancelDocument).toHaveBeenCalledWith('failed-document'),
    );
    await waitFor(() => expect(result.current.error).toBe('上传失败'));
    expect(result.current.progress).toBe(0);
  });

  it('keeps a document after an uncertain completion response', async () => {
    runtime.importDocument.mockImplementation(
      async (
        _file,
        _key,
        observer: {
          onPhase: (phase: string) => void;
          onResource: (id: string) => void;
        },
      ) => {
        observer.onResource('completed-document');
        observer.onPhase('completing');
        throw new Error('response lost');
      },
    );
    const { result } = renderHook(() => useDocumentImport(vi.fn()));

    act(() =>
      result.current.selectFile(
        new File(['screenplay'], 'script.txt', { type: 'text/plain' }),
      ),
    );
    act(() => void result.current.start());

    await waitFor(() => expect(result.current.error).toBe('上传失败'));
    expect(runtime.cancelDocument).not.toHaveBeenCalled();
  });
});

function aborted(signal: AbortSignal): Promise<never> {
  return new Promise((_, reject) => {
    signal.addEventListener('abort', () => {
      reject(new DOMException('aborted', 'AbortError'));
    });
  });
}
