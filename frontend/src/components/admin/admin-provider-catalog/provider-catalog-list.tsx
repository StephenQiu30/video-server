import { PencilSimple, Trash } from '@phosphor-icons/react';
import {
  type BulkDeleteOptions,
  BulkDeleteSelection,
} from '@/components/layout/bulk-delete-selection';
import { DataTable } from '@/components/layout/data-table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

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
      <DataTable<API.ProviderCatalogEntryResponse>
        data={items}
        getRowId={(item) => item.key}
        getRowLabel={(item) => item.display_name}
        caption="平台目录列表"
        className="min-w-[720px] table-fixed"
        columns={[
          {
            id: '平台',
            header: '平台',
            className: 'whitespace-normal',
            cell: (item) => <> {item.display_name} </>,
          },
          {
            id: '目录键',
            header: '目录键',
            className: 'whitespace-normal',
            cell: (item) => <> {item.key} </>,
          },
          {
            id: '注册与可见性',
            header: '注册与可见性',
            className: 'whitespace-normal',
            cell: (item) => <> {badges(item)} </>,
          },
          {
            id: '排序',
            header: '排序',
            className: 'text-right tabular-nums whitespace-normal',
            cell: (item) => <> {item.sort_order} </>,
          },
          {
            id: '操作',
            header: '操作',
            className: 'text-right whitespace-normal',
            cell: (item) => <> {actions(item)} </>,
          },
        ]}
      />
    </BulkDeleteSelection>
  );
}
