import { Info } from '@phosphor-icons/react';
import { createElement, type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import type { ScreenplayDocument } from '@/types/video';
import type { MarkdownHeading } from './screenplay-document-toc';

function renderHeading(
  cursor: { current: number },
  headings: MarkdownHeading[],
  as: 'h2' | 'h3' | 'h4',
  className: string,
  children: ReactNode,
) {
  const heading = headings[cursor.current];
  cursor.current += 1;

  return createElement(as, { className, id: heading?.id }, children);
}

function escapeHtmlTagsForDisplay(markdown: string) {
  return markdown.replace(/<\/?[a-z][^>]*>/gi, (tag) =>
    tag.replace('<', '&lt;').replace('>', '&gt;'),
  );
}

export function ScreenplayDocumentPreview({
  document,
  headings,
}: {
  document: ScreenplayDocument;
  headings: MarkdownHeading[];
}) {
  const headingCursor = { current: 0 };

  return (
    <section
      aria-labelledby="screenplay-preview-title"
      className="min-w-0 lg:grid lg:h-full lg:min-h-0 lg:grid-rows-[auto_minmax(0,1fr)_auto]"
      data-testid="screenplay-preview-column"
    >
      <div className="flex items-baseline justify-between gap-4">
        <h2
          className="text-lg font-medium tracking-[-0.02em]"
          id="screenplay-preview-title"
        >
          规范化剧本
        </h2>
        {document.preview ? (
          <span className="text-xs text-muted-foreground">Markdown 预览</span>
        ) : null}
      </div>
      {document.status === 'ready' && document.preview ? (
        <>
          <article
            aria-label="规范化剧本 Markdown 预览"
            className="mt-4 h-[clamp(28rem,72vh,56rem)] overflow-y-auto overscroll-contain bg-surface px-5 py-6 text-[15px] leading-7 text-foreground scrollbar-thin sm:px-8 sm:py-8 lg:h-auto lg:min-h-0"
            data-testid="screenplay-markdown-reader"
          >
            <ReactMarkdown
              allowedElements={[
                'blockquote',
                'br',
                'code',
                'del',
                'em',
                'h1',
                'h2',
                'h3',
                'h4',
                'h5',
                'h6',
                'hr',
                'li',
                'ol',
                'p',
                'pre',
                'strong',
                'table',
                'tbody',
                'td',
                'th',
                'thead',
                'tr',
                'ul',
              ]}
              components={{
                blockquote: ({ children }) => (
                  <blockquote className="my-5 rounded-md bg-muted/60 px-4 py-2 text-muted-foreground">
                    {children}
                  </blockquote>
                ),
                code: ({ children }) => (
                  <code className="font-mono text-[0.92em] text-foreground">
                    {children}
                  </code>
                ),
                h1: ({ children }) =>
                  renderHeading(
                    headingCursor,
                    headings,
                    'h2',
                    'mb-6 mt-2 scroll-mt-8 text-2xl font-medium tracking-[-0.03em] sm:text-3xl',
                    children,
                  ),
                h2: ({ children }) =>
                  renderHeading(
                    headingCursor,
                    headings,
                    'h3',
                    'mb-4 mt-10 scroll-mt-8 text-xl font-medium tracking-[-0.02em] sm:text-2xl',
                    children,
                  ),
                h3: ({ children }) =>
                  renderHeading(
                    headingCursor,
                    headings,
                    'h4',
                    'mb-3 mt-8 scroll-mt-8 text-base font-semibold uppercase tracking-[0.08em] sm:text-lg',
                    children,
                  ),
                h4: ({ children }) => (
                  <h5 className="mb-2 mt-6 scroll-mt-8 text-sm font-semibold uppercase tracking-[0.06em]">
                    {children}
                  </h5>
                ),
                h5: ({ children }) => (
                  <h6 className="mb-2 mt-5 scroll-mt-8 text-sm font-medium">
                    {children}
                  </h6>
                ),
                h6: ({ children }) => (
                  <p className="mb-2 mt-5 scroll-mt-8 text-sm font-medium">
                    {children}
                  </p>
                ),
                hr: () => <hr className="my-8 border-0" />,
                li: ({ children }) => <li className="pl-1">{children}</li>,
                ol: ({ children }) => (
                  <ol className="my-4 list-decimal space-y-1 pl-6">
                    {children}
                  </ol>
                ),
                p: ({ children }) => (
                  <p className="my-4 whitespace-pre-wrap">{children}</p>
                ),
                pre: ({ children }) => (
                  <pre className="my-5 overflow-x-auto rounded-md bg-muted/60 px-4 py-3 font-mono text-xs leading-6">
                    {children}
                  </pre>
                ),
                strong: ({ children }) => (
                  <strong className="font-semibold">{children}</strong>
                ),
                table: ({ children }) => (
                  <div className="my-5 overflow-x-auto">
                    <table className="min-w-full border-collapse text-left text-sm">
                      {children}
                    </table>
                  </div>
                ),
                th: ({ children }) => (
                  <th className="bg-muted/50 px-3 py-2 font-medium">
                    {children}
                  </th>
                ),
                td: ({ children }) => <td className="px-3 py-2">{children}</td>,
                ul: ({ children }) => (
                  <ul className="my-4 list-disc space-y-1 pl-6">{children}</ul>
                ),
              }}
              remarkPlugins={[remarkGfm]}
              skipHtml
              unwrapDisallowed
              urlTransform={() => ''}
            >
              {escapeHtmlTagsForDisplay(document.preview)}
            </ReactMarkdown>
          </article>
          {document.preview_truncated ? (
            <Alert className="mt-4" variant="default">
              <Info aria-hidden />
              <div className="min-w-0">
                <AlertTitle>预览已截断</AlertTitle>
                <AlertDescription>
                  当前内容仍受接口读取上限约束，只显示了文件开头的一段。
                </AlertDescription>
              </div>
            </Alert>
          ) : null}
        </>
      ) : (
        <div className="mt-4 py-16 text-sm text-muted-foreground">
          {previewStatusMessage(document.status)}
        </div>
      )}
    </section>
  );
}

function previewStatusMessage(status: ScreenplayDocument['status']) {
  if (status === 'uploading') return '文件上传完成后，这里会显示提取结果。';
  if (status === 'verifying') return '正在解析剧本文本，请稍后刷新。';
  if (status === 'ready') return '文档已解析，但当前没有可显示的预览。';
  if (status === 'failed') return '解析失败，未生成规范化剧本文本。';
  if (status === 'cancelled') return '导入已取消，未生成剧本文本。';
  return '文档已过期，预览不再可用。';
}
