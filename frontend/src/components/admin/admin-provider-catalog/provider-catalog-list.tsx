import { PencilSimple, Trash } from '@phosphor-icons/react';

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
  items: API.ProviderCatalogEntryResponse[];
  onDelete: (item: API.ProviderCatalogEntryResponse) => void;
  onEdit: (item: API.ProviderCatalogEntryResponse) => void;
};

export function ProviderCatalogList({
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
          className="text-destructive hover:text-destructive"
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
    <Table className="min-w-[720px] table-fixed">
      <TableCaption className="sr-only">平台目录列表</TableCaption>
      <TableHeader className="bg-muted/35">
        <TableRow className="hover:bg-transparent">
          <TableHead className="px-4">平台</TableHead>
          <TableHead className="px-4">目录键</TableHead>
          <TableHead className="px-4">注册与可见性</TableHead>
          <TableHead className="px-4 text-right">排序</TableHead>
          <TableHead className="px-4 text-right">操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item) => (
          <TableRow key={item.key}>
            <TableCell className="px-4 py-5 font-medium">
              {item.display_name}
            </TableCell>
            <TableCell className="px-4 py-5 font-mono text-xs text-muted-foreground">
              {item.key}
            </TableCell>
            <TableCell className="px-4 py-5">{badges(item)}</TableCell>
            <TableCell className="px-4 py-5 text-right text-xs tabular-nums">
              {item.sort_order}
            </TableCell>
            <TableCell className="px-4 py-5 text-right">
              {actions(item)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
