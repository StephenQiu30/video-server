import { PencilSimple, Trash } from '@phosphor-icons/react';
import { Fragment } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemFooter,
  ItemGroup,
  ItemSeparator,
  ItemTitle,
} from '@/components/ui/item';
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
        <Badge variant={item.system_registered ? 'success' : 'warning'}>
          {item.system_registered ? '系统已注册' : '仅目录'}
        </Badge>
        <Badge variant={item.is_visible ? 'neutral' : 'outline'}>
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
          className="h-11"
          onClick={() => onEdit(item)}
          size="sm"
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
    <>
      <div className="hairline hidden border-y md:block">
        <Table className="table-fixed">
          <TableCaption className="sr-only">平台目录列表</TableCaption>
          <TableHeader className="bg-muted/35">
            <TableRow className="hairline hover:bg-transparent">
              <TableHead className="w-[25%] px-4">平台</TableHead>
              <TableHead className="w-[22%] px-4">目录键</TableHead>
              <TableHead className="w-[28%] px-4">注册与可见性</TableHead>
              <TableHead className="w-[10%] px-4 text-right">排序</TableHead>
              <TableHead className="w-[15%] px-4 text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow className="hairline" key={item.key}>
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
      </div>
      <ItemGroup className="hairline gap-0 border-y md:hidden">
        {items.map((item, index) => (
          <Fragment key={item.key}>
            <Item className="rounded-none border-0 px-0 py-5" role="listitem">
              <ItemContent className="min-w-0">
                <ItemTitle>{item.display_name}</ItemTitle>
                <ItemDescription>
                  <span className="font-mono">{item.key}</span> · 排序{' '}
                  <span className="tabular-nums">{item.sort_order}</span>
                </ItemDescription>
              </ItemContent>
              <ItemActions>{actions(item)}</ItemActions>
              <ItemFooter>{badges(item)}</ItemFooter>
            </Item>
            {index < items.length - 1 ? (
              <ItemSeparator className="hairline my-0" />
            ) : null}
          </Fragment>
        ))}
      </ItemGroup>
    </>
  );
}
