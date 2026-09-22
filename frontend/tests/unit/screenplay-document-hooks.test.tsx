import { act, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useScreenplayDocument } from '@/components/screenplay/use-screenplay-document';
import { useScreenplayDocuments } from '@/components/screenplay/use-screenplay-documents';
import {
  screenplayDocument,
  screenplayDocumentPage,
} from '../fixtures/document-fixtures';
import { renderHook } from '../helpers/query-render';

const runtime = vi.hoisted(() => ({
  getScreenplayDocument: vi.fn(),
  listScreenplayDocuments: vi.fn(),
}));

describe('screenplay document hooks', () => {
  beforeEach(() => {
    runtime.getScreenplayDocument.mockReset();
    runtime.listScreenplayDocuments.mockReset();
  });

  it('maps pagination and refresh to the typed document service', async () => {
    runtime.listScreenplayDocuments.mockResolvedValue(screenplayDocumentPage());
    const { result, rerender } = renderHook(
      ({ page }: { page: number }) =>
        useScreenplayDocuments({ page, page_size: 20 }),
      { initialProps: { page: 1 } },
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(runtime.listScreenplayDocuments).toHaveBeenLastCalledWith(
      {
        page: 1,
        page_size: 20,
      },
      { signal: expect.any(AbortSignal) },
    );
    rerender({ page: 2 });
    await waitFor(() =>
      expect(runtime.listScreenplayDocuments).toHaveBeenLastCalledWith(
        {
          page: 2,
          page_size: 20,
        },
        { signal: expect.any(AbortSignal) },
      ),
    );
    act(() => result.current.refresh());
    await waitFor(() =>
      expect(runtime.listScreenplayDocuments).toHaveBeenCalledTimes(3),
    );
  });

  it('does not expose the previous document while a new id is loading', async () => {
    let resolveSecond:
      | ((value: ReturnType<typeof screenplayDocument>) => void)
      | null = null;
    runtime.getScreenplayDocument
      .mockResolvedValueOnce(screenplayDocument({ id: 'first-id' }))
      .mockImplementationOnce(
        () =>
          new Promise<ReturnType<typeof screenplayDocument>>((resolve) => {
            resolveSecond = resolve;
          }),
      );
    const { result, rerender } = renderHook(
      ({ documentId }: { documentId: string }) =>
        useScreenplayDocument(documentId, 60_000),
      { initialProps: { documentId: 'first-id' } },
    );

    await waitFor(() => expect(result.current.document?.id).toBe('first-id'));
    rerender({ documentId: 'second-id' });
    expect(result.current.document).toBeNull();
    expect(result.current.loading).toBe(true);

    act(() => resolveSecond?.(screenplayDocument({ id: 'second-id' })));
    await waitFor(() => expect(result.current.document?.id).toBe('second-id'));
  });

  it('ignores a polling response that belongs to the previous document id', async () => {
    const stalePoll = deferred<ReturnType<typeof screenplayDocument>>();
    runtime.getScreenplayDocument
      .mockResolvedValueOnce(
        screenplayDocument({ id: 'first-id', status: 'uploading' }),
      )
      .mockReturnValueOnce(stalePoll.promise)
      .mockResolvedValueOnce(
        screenplayDocument({ id: 'second-id', title: 'Second screenplay' }),
      );
    const { result, rerender } = renderHook(
      ({ documentId }: { documentId: string }) =>
        useScreenplayDocument(documentId, 10),
      { initialProps: { documentId: 'first-id' } },
    );

    await waitFor(() => expect(result.current.document?.id).toBe('first-id'));
    await waitFor(() =>
      expect(runtime.getScreenplayDocument).toHaveBeenCalledTimes(2),
    );
    rerender({ documentId: 'second-id' });
    await waitFor(() => expect(result.current.document?.id).toBe('second-id'));

    await act(async () => {
      stalePoll.resolve(
        screenplayDocument({ id: 'first-id', title: 'Stale screenplay' }),
      );
    });
    expect(result.current.document?.title).toBe('Second screenplay');
  });

  it('stops polling after an upload session has failed', async () => {
    runtime.getScreenplayDocument.mockResolvedValue(
      screenplayDocument({
        error_code: 'upload_session_expired',
        id: 'expired-upload',
        status: 'uploading',
      }),
    );
    const { result } = renderHook(() =>
      useScreenplayDocument('expired-upload', 10),
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 40));
    });

    expect(runtime.getScreenplayDocument).toHaveBeenCalledOnce();
  });
});

vi.mock('@/lib/request-error', async (original) => ({
  ...(await original<typeof import('@/lib/request-error')>()),
  displayError: (reason: unknown) =>
    reason instanceof Error ? reason.message : '请求失败',
}));
vi.mock('@/api/documents', async (original) => ({
  ...(await original<typeof import('@/api/documents')>()),
  getDocumentImport: runtime.getScreenplayDocument,
  listDocuments: runtime.listScreenplayDocuments,
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
