import { Trash } from '@phosphor-icons/react';

import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import {
  formatStorageDate,
  formatStorageSize,
  storageCategoryLabels,
} from './model';

export function StorageFileList({
  items,
  onDelete,
}: {
  items: API.StoredFileResponse[];
  onDelete: (item: API.StoredFileResponse) => void;
}) {
  return (
    <div className="overflow-hidden rounded-md">
      <Table className="table-fixed">
        <TableCaption className="sr-only">持久文件列表</TableCaption>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="px-3">文件</TableHead>
            <TableHead className="px-3">类型</TableHead>
            <TableHead className="px-3 text-right">对象数</TableHead>
            <TableHead className="px-3">创建时间</TableHead>
            <TableHead className="px-3 text-right">大小</TableHead>
            <TableHead className="px-3 text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <TableRow key={`${item.category}-${item.id}`}>
              <TableCell className="max-w-0 truncate px-3 py-2 font-medium">
                <span className="block truncate" title={item.name}>
                  {item.name}
                </span>
              </TableCell>
              <TableCell className="px-3 py-2 text-muted-foreground">
                {storageCategoryLabels[item.category]}
              </TableCell>
              <TableCell className="px-3 py-2 text-right text-xs tabular-nums">
                {item.object_count}
              </TableCell>
              <TableCell className="px-3 py-2 text-xs text-muted-foreground tabular-nums">
                {formatStorageDate(item.created_at)}
              </TableCell>
              <TableCell className="px-3 py-2 text-right text-sm font-medium tabular-nums">
                {formatStorageSize(item.size_bytes)}
              </TableCell>
              <TableCell className="px-3 py-2 text-right">
                <Button
                  aria-label={`删除文件 ${item.name}`}
                  className="text-destructive hover:text-destructive"
                  onClick={() => onDelete(item)}
                  size="icon-lg"
                  type="button"
                  variant="ghost"
                >
                  <Trash aria-hidden />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
