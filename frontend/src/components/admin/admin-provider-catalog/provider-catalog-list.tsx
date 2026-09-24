import { PencilSimple, Trash } from '@phosphor-icons/react';
import {
  type BulkDeleteOptions,
  BulkDeleteSelection,
  SelectionCell,
  SelectionHead,
} from '@/components/layout/bulk-delete-selection';

import { Badge } from '@/components/ui/badge';
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

type ProviderCatalogListProps = {
  bulk?: BulkDeleteOptions;
  items: API.ProviderCatalogEntryResponse[];
  onDelete: (item: API.ProviderCatalogEntryResponse) => void;
  onEdit: (item: API.ProviderCatalogEntryResponse) => void;
};

export function ProviderCatalogList({
  bulk,
  items,
  onDelete,
  onEdit,
}: ProviderCatalogListProps) {
  function badges(item: API.ProviderCatalogEntryResponse) {
    return (
      <span className="flex flex-wrap gap-1.5">
        <Badge variant={item.system_registered ? 'default' : 'secondary'}>
          {item.system_registered ? '系统已注册' : '仅目录'}
        </Badge>
        <Badge variant={item.is_visible ? 'secondary' : 'outline'}>
          {item.is_visible ? '公开显示' : '已隐藏'}
        </Badge>
      </span>
    );
  }

  function actions(item: API.ProviderCatalogEntryResponse) {
    return (
      <span className="inline-flex items-center justify-end gap-0.5">
        <Button
          aria-label={`编辑平台 ${item.display_name}`}
          onClick={() => onEdit(item)}
          size="lg"
          type="button"
          variant="ghost"
        >
          <PencilSimple aria-hidden />
          编辑
        </Button>
        <Button
          aria-label={`删除平台 ${item.display_name}`}
          onClick={() => onDelete(item)}
          size="icon-lg"
          type="button"
          variant="ghost"
        >
          <Trash aria-hidden />
        </Button>
      </span>
    );
  }

  return (
    <BulkDeleteSelection ids={items.map((item) => item.key)} options={bulk}>
      <Table className="min-w-[720px] table-fixed">
        <TableCaption className="sr-only">平台目录列表</TableCaption>
        <TableHeader>
          <TableRow>
            <SelectionHead />
            <TableHead>平台</TableHead>
            <TableHead>目录键</TableHead>
            <TableHead>注册与可见性</TableHead>
            <TableHead className="text-right">排序</TableHead>
            <TableHead className="text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.key}>
              <SelectionCell id={item.key} label={item.display_name} />
              <TableCell>{item.display_name}</TableCell>
              <TableCell>{item.key}</TableCell>
              <TableCell>{badges(item)}</TableCell>
              <TableCell className="text-right tabular-nums">
                {item.sort_order}
              </TableCell>
              <TableCell className="text-right">{actions(item)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </BulkDeleteSelection>
  );
}
