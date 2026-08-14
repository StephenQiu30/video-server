import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MissingScreenplayDocument } from '@/components/missing-screenplay-document';
import ScreenplayDocumentDetailView from '@/components/screenplay-document-detail-view';
import ScreenplayDocumentsView from '@/components/screenplay-documents-view';
import {
  screenplayDocument,
  screenplayDocumentPage,
  screenplayDocumentSummary,
} from '../fixtures/document-fixtures';

const runtime = vi.hoisted(() => ({
  getScreenplayDocument: vi.fn(),
  listScreenplayDocuments: vi.fn(),
}));

vi.mock('@/services/documents', () => ({
  displayError: (reason: unknown) =>
    reason instanceof Error ? reason.message : '请求失败',
  getScreenplayDocument: runtime.getScreenplayDocument,
  listScreenplayDocuments: runtime.listScreenplayDocuments,
}));

describe('screenplay documents', () => {
  beforeEach(() => {
    runtime.getScreenplayDocument.mockReset();
    runtime.listScreenplayDocuments.mockReset();
  });

  it('renders metadata rows, paging and a stable refresh action', async () => {
    runtime.listScreenplayDocuments.mockImplementation(
      async ({ page = 1 }: { page?: number }) =>
        screenplayDocumentPage({
          items: [screenplayDocumentSummary()],
          page,
          total: 21,
        }),
    );
    render(<ScreenplayDocumentsView />);

    expect(screen.getByRole('status')).toHaveTextContent('正在加载剧本文档');
    expect(await screen.findByText('午夜来客')).toBeInTheDocument();
    expect(screen.getByText('Fountain')).toBeInTheDocument();
    expect(screen.getByText(/2 个场景/)).toBeInTheDocument();
    expect(screen.getByText(/中英混合/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '午夜来客' })).toHaveAttribute(
      'href',
      '/documents/detail?documentId=99999999-9999-4999-8999-999999999999',
    );
    fireEvent.click(screen.getByRole('button', { name: '下一页' }));
    await waitFor(() =>
      expect(runtime.listScreenplayDocuments).toHaveBeenLastCalledWith({
        page: 2,
        page_size: 20,
      }),
    );
    fireEvent.click(screen.getByRole('button', { name: '刷新' }));
    await waitFor(() =>
      expect(runtime.listScreenplayDocuments).toHaveBeenCalledTimes(3),
    );
  });

  it('keeps the empty and request-failure states actionable', async () => {
    runtime.listScreenplayDocuments.mockResolvedValueOnce(
      screenplayDocumentPage({ items: [], total: 0 }),
    );
    const { unmount } = render(<ScreenplayDocumentsView />);
    expect(await screen.findByText('还没有剧本文档')).toBeInTheDocument();
    unmount();

    runtime.listScreenplayDocuments.mockRejectedValueOnce(
      new Error('文档服务暂时不可用'),
    );
    render(<ScreenplayDocumentsView />);
    expect(await screen.findByText('文档服务暂时不可用')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '刷新' })).toBeInTheDocument();
  });

  it('renders HTML-like screenplay content only as bounded plain text', async () => {
    runtime.getScreenplayDocument.mockResolvedValue(
      screenplayDocument({ id: 'document-id' }),
    );
    const { container } = render(
      <ScreenplayDocumentDetailView documentId="document-id" />,
    );

    expect(screen.getByRole('status')).toHaveTextContent('正在读取剧本文档');
    expect(
      await screen.findByRole('heading', { level: 1, name: '午夜来客' }),
    ).toBeInTheDocument();
    const preview = container.querySelector('pre');
    expect(preview).toHaveTextContent('<script>只作为台词文本</script>');
    expect(container.querySelector('script')).toBeNull();
    const truncationTitle = screen.getByText('预览已截断');
    expect(truncationTitle.parentElement).toHaveTextContent(
      '这里只显示文件开头的一段',
    );
    const warningTitle = screen.getByText('需要人工核对');
    expect(warningTitle.parentElement).toHaveTextContent(
      '未识别到明确场景标题',
    );
    expect(screen.getByText('中英混合')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '返回上一步' })).toHaveAttribute(
      'href',
      '/documents',
    );
  });

  it('explains active, failed and missing document states', async () => {
    runtime.getScreenplayDocument.mockResolvedValueOnce(
      screenplayDocument({
        id: 'verifying-id',
        preview: null,
        preview_truncated: false,
        status: 'verifying',
      }),
    );
    const { unmount } = render(
      <ScreenplayDocumentDetailView
        documentId="verifying-id"
        pollIntervalMs={60_000}
      />,
    );
    expect(
      await screen.findByText('正在解析剧本文本，请稍后刷新。'),
    ).toBeInTheDocument();
    unmount();

    runtime.getScreenplayDocument.mockResolvedValueOnce(
      screenplayDocument({
        error_code: 'document_text_unavailable',
        id: 'failed-id',
        preview: null,
        preview_truncated: false,
        status: 'failed',
      }),
    );
    const failedView = render(
      <ScreenplayDocumentDetailView documentId="failed-id" />,
    );
    expect(
      await screen.findByText('没有提取到可用的剧本文本。'),
    ).toBeInTheDocument();
    failedView.unmount();

    runtime.getScreenplayDocument.mockRejectedValueOnce(
      new Error('文档服务暂时不可用'),
    );
    const requestFailure = render(
      <ScreenplayDocumentDetailView documentId="unavailable-id" />,
    );
    expect(
      await screen.findByRole('heading', { name: '无法读取剧本文档' }),
    ).toBeInTheDocument();
    expect(screen.getByText('文档服务暂时不可用')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重试' })).toBeInTheDocument();
    requestFailure.unmount();

    render(<MissingScreenplayDocument />);
    expect(
      screen.getByRole('heading', { name: '剧本文档不存在' }),
    ).toBeInTheDocument();
  });
});
