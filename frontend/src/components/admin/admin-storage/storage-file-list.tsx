import { Trash } from '@phosphor-icons/react';
import {
  type BulkDeleteOptions,
  BulkDeleteSelection,
  SelectionCell,
  SelectionHead,
} from '@/components/layout/bulk-delete-selection';

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
  bulk,
  items,
  onDelete,
}: {
  bulk?: BulkDeleteOptions;
  items: API.StoredFileResponse[];
  onDelete: (item: API.StoredFileResponse) => void;
}) {
  return (
    <BulkDeleteSelection
      ids={items.map((item) => `${item.category}:${item.id}`)}
      options={bulk}
    >
      <div className="overflow-hidden rounded-md">
        <Table className="min-w-[900px] table-fixed">
          <TableCaption className="sr-only">持久文件列表</TableCaption>
          <TableHeader>
            <TableRow>
              <SelectionHead />
              <TableHead>文件</TableHead>
              <TableHead>类型</TableHead>
              <TableHead className="text-right">对象数</TableHead>
              <TableHead>创建时间</TableHead>
              <TableHead className="text-right">大小</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow key={`${item.category}-${item.id}`}>
                <SelectionCell
                  id={`${item.category}:${item.id}`}
                  label={item.name}
                />
                <TableCell className="max-w-0 truncate">
                  <span className="block truncate" title={item.name}>
                    {item.name}
                  </span>
                </TableCell>
                <TableCell>{storageCategoryLabels[item.category]}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {item.object_count}
                </TableCell>
                <TableCell className="tabular-nums">
                  {formatStorageDate(item.created_at)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatStorageSize(item.size_bytes)}
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    aria-label={`删除文件 ${item.name}`}
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
    </BulkDeleteSelection>
  );
}
