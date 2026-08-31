import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MissingScreenplayDocument } from '@/components/screenplay/missing-screenplay-document';
import ScreenplayDocumentDetailView from '@/components/screenplay/screenplay-document-detail-view';
import ScreenplayDocumentsView from '@/components/screenplay/screenplay-documents-view';
import {
  screenplayDocument,
  screenplayDocumentPage,
  screenplayDocumentSummary,
} from '../fixtures/document-fixtures';

const runtime = vi.hoisted(() => ({
  getScreenplayDocument: vi.fn(),
  listScreenplayDocuments: vi.fn(),
  push: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: runtime.push }),
}));

vi.mock('@/services/documents', () => ({
  displayError: (reason: unknown) =>
    reason instanceof Error ? reason.message : '请求失败',
  getScreenplayDocument: runtime.getScreenplayDocument,
  listScreenplayDocuments: runtime.listScreenplayDocuments,
}));

vi.mock('@/components/screenplay/screenplay-analysis-panel', () => ({
  default: ({ documentId }: { documentId: string }) => (
    <section aria-label="剧本分析工作区">{documentId}</section>
  ),
}));

describe('screenplay documents', () => {
  beforeEach(() => {
    runtime.getScreenplayDocument.mockReset();
    runtime.listScreenplayDocuments.mockReset();
    runtime.push.mockReset();
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

  it('exposes screenplay upload as the primary empty-state entry', async () => {
    runtime.listScreenplayDocuments.mockResolvedValueOnce(
      screenplayDocumentPage({ items: [], total: 0 }),
    );
    render(<ScreenplayDocumentsView />);

    await screen.findByText('还没有剧本文档');
    fireEvent.click(screen.getByRole('button', { name: '上传剧本' }));
    expect(
      screen.getByRole('heading', { name: '上传剧本文档' }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '上传剧本' }));
    expect(screen.getByText('请先选择一份剧本文档。')).toBeInTheDocument();
  });

  it('renders screenplay Markdown safely with a fixed reader and table of contents', async () => {
    runtime.getScreenplayDocument.mockResolvedValue(
      screenplayDocument({
        id: 'document-id',
        preview:
          '# 午夜来客\n\n## INT. LOBBY - NIGHT\n\n<script>只作为台词文本</script>\n\nA visitor waits in the lobby.',
      }),
    );
    const { container } = render(
      <ScreenplayDocumentDetailView documentId="document-id" />,
    );

    expect(screen.getByRole('status')).toHaveTextContent('正在读取剧本文档');
    expect(
      await screen.findByRole('heading', { level: 1, name: '午夜来客' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 2, name: '午夜来客' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 3, name: 'INT. LOBBY - NIGHT' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('article', { name: '规范化剧本 Markdown 预览' }),
    ).toHaveTextContent('<script>只作为台词文本</script>');
    expect(container.querySelector('script')).toBeNull();
    expect(container.querySelector('pre')).toBeNull();
    expect(screen.getByTestId('screenplay-markdown-reader')).toHaveClass(
      'h-[clamp(28rem,72vh,56rem)]',
      'lg:h-auto',
      'lg:min-h-0',
    );
    const workspace = screen.getByTestId('screenplay-document-workspace');
    expect(workspace).toHaveClass(
      'lg:h-[clamp(34rem,72vh,56rem)]',
      'lg:grid-rows-[minmax(0,1fr)]',
      'lg:overflow-hidden',
    );
    expect(screen.getByTestId('screenplay-preview-column')).toHaveClass(
      'lg:grid-rows-[auto_minmax(0,1fr)_auto]',
      'lg:min-h-0',
    );
    const tableOfContents = screen.getByRole('navigation', { name: '目录' });
    expect(tableOfContents).toHaveAttribute('data-slot', 'navigation-menu');
    expect(tableOfContents).toHaveClass(
      'lg:grid',
      'lg:h-full',
      'lg:grid-rows-[auto_minmax(0,1fr)]',
      'lg:overflow-hidden',
    );
    expect(screen.getByRole('link', { name: '午夜来客' })).toHaveAttribute(
      'href',
      '#screenplay-heading-0',
    );
    expect(
      screen.getByRole('link', { name: 'INT. LOBBY - NIGHT' }),
    ).toHaveAttribute('href', '#screenplay-heading-1');
    expect(
      screen.getByRole('heading', { name: '文档信息' }).closest('section'),
    ).toHaveTextContent('导入摘要');
    const truncationTitle = screen.getByText('预览已截断');
    expect(truncationTitle.parentElement).toHaveTextContent(
      '当前内容仍受接口读取上限约束',
    );
    const warningTitle = screen.getByText('需要人工核对');
    expect(warningTitle.parentElement).toHaveTextContent(
      '未识别到明确场景标题',
    );
    expect(screen.getByText('中英混合')).toBeInTheDocument();
    const analysis = screen.getByLabelText('剧本分析工作区');
    expect(analysis).toHaveTextContent('document-id');
    expect(workspace.nextElementSibling).toBe(analysis);
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
