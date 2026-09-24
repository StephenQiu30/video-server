import { FileText } from '@phosphor-icons/react';
import Link from 'next/link';
import { PageEmptyNotice } from '@/components/layout/page-empty-notice';
import { ScreenplayDocumentDeleteDialog } from '@/components/screenplay/screenplay-document-delete-dialog';
import {
  documentFormatLabels,
  documentStatusLabels,
  documentStatusVariant,
  formatDocumentDate,
  languageLabel,
} from '@/components/screenplay/screenplay-document-format';
import { ScreenplayUploadDialog } from '@/components/screenplay/screenplay-upload-dialog';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

export function ScreenplayDocumentList({
  data,
  loading,
  onDelete,
  pendingDeleteId,
}: {
  data: API.DocumentPageResponse | null;
  loading: boolean;
  onDelete: (document: API.DocumentResponse) => Promise<void>;
  pendingDeleteId: string | null;
}) {
  return (
    <div aria-busy={loading} className="mt-10 sm:mt-12">
      {loading && !data ? <LoadingRows /> : null}
      {data?.items.length ? (
        <Table className="min-w-[900px] table-fixed">
          <TableCaption className="sr-only">剧本文档列表</TableCaption>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-[34%] px-3">文档</TableHead>
              <TableHead className="w-[15%] px-3">格式与更新时间</TableHead>
              <TableHead className="w-[22%] px-3">内容统计</TableHead>
              <TableHead className="w-[13%] px-3">状态</TableHead>
              <TableHead className="w-[16%] px-3 text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.map((document) => (
              <DocumentRow
                document={document}
                key={document.id}
                onDelete={onDelete}
                pending={pendingDeleteId === document.id}
              />
            ))}
          </TableBody>
        </Table>
      ) : null}
      {data && !data.items.length ? (
        <PageEmptyNotice
          action={<ScreenplayUploadDialog label="上传第一份剧本" />}
          description="上传一份剧本文档后，可在这里核对解析状态与正文。"
          icon={<FileText aria-hidden />}
          title="还没有剧本文档"
        />
      ) : null}
    </div>
  );
}

function DocumentRow({
  document,
  onDelete,
  pending,
}: {
  document: API.DocumentResponse;
  onDelete: (document: API.DocumentResponse) => Promise<void>;
  pending: boolean;
}) {
  const detailHref = `/documents/detail?documentId=${encodeURIComponent(document.id)}`;
  return (
    <TableRow>
      <TableHead
        className="max-w-0 px-3 py-2 text-left align-middle whitespace-normal"
        scope="row"
      >
        <div className="flex min-w-0 flex-col gap-1">
          <Link
            className="focus-ring line-clamp-2 rounded-sm text-[15px] font-medium leading-snug hover:text-muted-foreground"
            href={detailHref}
          >
            {document.title}
          </Link>
          <span className="truncate text-xs text-muted-foreground">
            {document.original_filename}
          </span>
        </div>
      </TableHead>
      <TableCell className="px-3 py-2 text-xs text-muted-foreground whitespace-normal">
        <div className="flex flex-col gap-1">
          <span>{documentFormatLabels[document.source_format]}</span>
          <time dateTime={document.updated_at}>
            {formatDocumentDate(document.updated_at)}
          </time>
        </div>
      </TableCell>
      <TableCell className="px-3 py-2 text-sm whitespace-normal">
        <div className="flex flex-col gap-1">
          <span>
            {document.scene_count ?? '-'} 个场景 ·{' '}
            {document.character_count?.toLocaleString('zh-CN') ?? '-'} 个字符
          </span>
          <span className="text-xs text-muted-foreground">
            {languageLabel(document.detected_language)}
          </span>
        </div>
      </TableCell>
      <TableCell className="px-3 py-2">
        <Badge
          className="rounded-md px-2 py-1 font-normal"
          variant={documentStatusVariant(document.status)}
        >
          {documentStatusLabels[document.status]}
        </Badge>
      </TableCell>
      <TableCell className="px-3 py-2 text-right">
        <ScreenplayDocumentDeleteDialog
          busy={pending}
          compact
          onDelete={() => onDelete(document)}
        />
      </TableCell>
    </TableRow>
  );
}

function LoadingRows() {
  return (
    <>
      <span className="sr-only" role="status">
        正在加载剧本文档
      </span>
      <div aria-hidden className="flex flex-col gap-2">
        {['first', 'second', 'third'].map((key) => (
          <div
            className="grid grid-cols-[minmax(0,1fr)_5rem] gap-5 py-6"
            key={key}
          >
            <div className="flex flex-col gap-2">
              <Skeleton className="h-5 w-2/5" />
              <Skeleton className="h-4 w-3/5" />
              <Skeleton className="h-4 w-1/2" />
            </div>
            <Skeleton className="h-6 w-20" />
          </div>
        ))}
      </div>
    </>
  );
}
