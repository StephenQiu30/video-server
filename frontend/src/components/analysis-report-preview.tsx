'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const allowedElements = [
  'blockquote',
  'code',
  'em',
  'h1',
  'h2',
  'h3',
  'hr',
  'li',
  'ol',
  'p',
  'strong',
  'table',
  'tbody',
  'td',
  'th',
  'thead',
  'tr',
  'ul',
];

export default function AnalysisReportPreview({
  markdown,
}: {
  markdown: string;
}) {
  return (
    <article
      aria-label="Markdown 分析报告预览"
      className="w-full text-[15px] leading-7"
    >
      <ReactMarkdown
        allowedElements={allowedElements}
        components={{
          blockquote: ({ children }) => (
            <blockquote className="my-5 border-l-2 pl-4 text-muted-foreground">
              {children}
            </blockquote>
          ),
          h1: ({ children }) => (
            <h3 className="mb-5 text-2xl font-medium tracking-[-0.03em]">
              {children}
            </h3>
          ),
          h2: ({ children }) => (
            <h4 className="mt-10 border-b pb-3 text-lg font-medium tracking-[-0.02em]">
              {children}
            </h4>
          ),
          h3: ({ children }) => (
            <h5 className="mt-7 font-medium">{children}</h5>
          ),
          li: ({ children }) => <li className="pl-1">{children}</li>,
          ol: ({ children }) => (
            <ol className="my-4 list-decimal space-y-1 pl-5">{children}</ol>
          ),
          p: ({ children }) => (
            <p className="my-3 text-muted-foreground">{children}</p>
          ),
          table: ({ children }) => (
            <div className="my-6 overflow-x-auto border-y">
              <table className="w-full border-collapse text-left text-sm">
                {children}
              </table>
            </div>
          ),
          td: ({ children }) => (
            <td className="border-t px-3 py-2 align-top">{children}</td>
          ),
          th: ({ children }) => (
            <th className="bg-muted px-3 py-2 font-medium">{children}</th>
          ),
          ul: ({ children }) => (
            <ul className="my-4 list-disc space-y-1 pl-5">{children}</ul>
          ),
        }}
        remarkPlugins={[remarkGfm]}
        skipHtml
        unwrapDisallowed
        urlTransform={() => ''}
      >
        {markdown}
      </ReactMarkdown>
    </article>
  );
}
