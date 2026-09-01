import Link from 'next/link';
import { ScreenplayDocumentDeleteDialog } from '@/components/screenplay/screenplay-document-delete-dialog';
import {
  documentFormatLabels,
  documentStatusLabels,
  documentStatusVariant,
  formatDocumentDate,
  languageLabel,
} from '@/components/screenplay/screenplay-document-format';
import { Badge } from '@/components/ui/badge';
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from '@/components/ui/empty';
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemTitle,
} from '@/components/ui/item';
import { Skeleton } from '@/components/ui/skeleton';
import type {
  ScreenplayDocumentPage,
  ScreenplayDocumentSummary,
} from '@/types/video';

export function ScreenplayDocumentList({
  data,
  loading,
  onDelete,
  pendingDeleteId,
}: {
  data: ScreenplayDocumentPage | null;
  loading: boolean;
  onDelete: (document: ScreenplayDocumentSummary) => Promise<void>;
  pendingDeleteId: string | null;
}) {
  return (
    <section
      aria-busy={loading}
      aria-label="剧本文档"
      className="mt-10 sm:mt-12"
    >
      {loading && !data ? <LoadingRows /> : null}
      {data?.items.length ? (
        <ItemGroup className="gap-2">
          {data.items.map((document) => (
            <DocumentRow
              document={document}
              key={document.id}
              onDelete={onDelete}
              pending={pendingDeleteId === document.id}
            />
          ))}
        </ItemGroup>
      ) : null}
      {data && !data.items.length ? (
        <Empty className="min-h-72 items-start rounded-none border-0 py-20 text-left">
          <EmptyHeader className="items-start">
            <EmptyTitle>还没有剧本文档</EmptyTitle>
            <EmptyDescription className="text-left">
              完成剧本文档上传后，可在这里核对解析状态与正文。
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : null}
    </section>
  );
}

function DocumentRow({
  document,
  onDelete,
  pending,
}: {
  document: ScreenplayDocumentSummary;
  onDelete: (document: ScreenplayDocumentSummary) => Promise<void>;
  pending: boolean;
}) {
  const detailHref = `/documents/detail?documentId=${encodeURIComponent(document.id)}`;
  return (
    <Item
      className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4 rounded-none border-0 px-0 py-6 sm:items-center sm:gap-8"
      role="listitem"
    >
      <ItemContent className="min-w-0 gap-2">
        <ItemTitle>
          <Link
            className="focus-ring line-clamp-2 rounded-sm text-[15px] font-medium leading-snug hover:text-muted-foreground"
            href={detailHref}
          >
            {document.title}
          </Link>
        </ItemTitle>
        <ItemDescription className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs sm:text-sm">
          <span className="max-w-full truncate">
            {document.original_filename}
          </span>
          <span aria-hidden>·</span>
          <span>{documentFormatLabels[document.source_format]}</span>
          <span aria-hidden>·</span>
          <time dateTime={document.updated_at}>
            {formatDocumentDate(document.updated_at)}
          </time>
        </ItemDescription>
        <p className="text-xs text-muted-foreground sm:text-sm">
          {document.scene_count ?? '—'} 个场景 ·{' '}
          {document.character_count?.toLocaleString('zh-CN') ?? '—'} 个字符 ·{' '}
          {languageLabel(document.detected_language)}
        </p>
      </ItemContent>
      <ItemActions className="self-start gap-1 sm:self-center">
        <Badge
          className="rounded-md px-2 py-1 font-normal"
          variant={documentStatusVariant(document.status)}
        >
          {documentStatusLabels[document.status]}
        </Badge>
        <ScreenplayDocumentDeleteDialog
          busy={pending}
          compact
          onDelete={() => onDelete(document)}
        />
      </ItemActions>
    </Item>
  );
}

function LoadingRows() {
  return (
    <>
      <span className="sr-only" role="status">
        正在加载剧本文档
      </span>
      <div aria-hidden className="space-y-2">
        {['first', 'second', 'third'].map((key) => (
          <div
            className="grid grid-cols-[minmax(0,1fr)_5rem] gap-5 py-6"
            key={key}
          >
            <div className="space-y-2">
              <Skeleton className="h-5 w-2/5" />
              <Skeleton className="h-4 w-3/5" />
              <Skeleton className="h-4 w-1/2" />
            </div>
            <Skeleton className="h-7 w-20" />
          </div>
        ))}
      </div>
    </>
  );
}
