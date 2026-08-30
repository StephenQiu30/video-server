'use client';

import { List } from '@phosphor-icons/react';

export type MarkdownHeading = {
  id: string;
  level: 1 | 2 | 3;
  text: string;
};

function cleanHeadingText(value: string) {
  return value
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/<[^>]+>/g, '')
    .replace(/[*_`~]/g, '')
    .trim();
}

export function extractMarkdownHeadings(markdown: string): MarkdownHeading[] {
  const headings: MarkdownHeading[] = [];
  let inCodeBlock = false;

  for (const line of markdown.split(/\r?\n/)) {
    if (/^\s*(```|~~~)/.test(line)) {
      inCodeBlock = !inCodeBlock;
      continue;
    }

    if (inCodeBlock) {
      continue;
    }

    const match = /^\s*(#{1,3})\s+(.+?)\s*#*\s*$/.exec(line);
    if (!match) {
      continue;
    }

    const text = cleanHeadingText(match[2]);
    if (!text) {
      continue;
    }

    headings.push({
      id: `screenplay-heading-${headings.length}`,
      level: match[1].length as MarkdownHeading['level'],
      text,
    });
  }

  return headings;
}

export function ScreenplayDocumentToc({
  headings,
}: {
  headings: MarkdownHeading[];
}) {
  return (
    <nav
      aria-labelledby="screenplay-toc-title"
      className="lg:grid lg:h-full lg:min-h-0 lg:grid-rows-[auto_minmax(0,1fr)] lg:overflow-hidden"
    >
      <div className="flex items-center justify-between gap-4 pb-3">
        <div className="flex items-center gap-2">
          <List
            aria-hidden
            className="size-4 text-muted-foreground"
            weight="regular"
          />
          <h2 className="text-sm font-medium" id="screenplay-toc-title">
            目录
          </h2>
        </div>
        {headings.length ? (
          <span className="text-xs text-muted-foreground">
            {headings.length} 节
          </span>
        ) : null}
      </div>

      {headings.length ? (
        <ol className="mt-3 space-y-0.5 lg:h-auto lg:min-h-0 lg:overflow-y-auto lg:overscroll-contain lg:scrollbar-thin">
          {headings.map((heading) => (
            <li key={heading.id}>
              <a
                className={`block rounded-md py-1.5 text-sm leading-5 text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                  heading.level === 1
                    ? 'px-3'
                    : heading.level === 2
                      ? 'pr-3 pl-6 text-[13px]'
                      : 'pr-3 pl-9 text-xs'
                }`}
                href={`#${heading.id}`}
              >
                {heading.text}
              </a>
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-4 text-sm leading-6 text-muted-foreground">
          当前文档没有可用的标题目录。
        </p>
      )}
    </nav>
  );
}
