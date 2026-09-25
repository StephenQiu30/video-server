import { Trash } from '@phosphor-icons/react';
import {
  type BulkDeleteOptions,
  BulkDeleteSelection,
} from '@/components/layout/bulk-delete-selection';
import { DataTable } from '@/components/layout/data-table';
import { Button } from '@/components/ui/button';

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
        <DataTable<API.StoredFileResponse>
          data={items}
          getRowId={(item) => `${item.category}:${item.id}`}
          getRowLabel={(item) => item.name}
          caption="持久文件列表"
          className="min-w-[900px] table-fixed"
          columns={[
            {
              id: '文件',
              header: '文件',
              className: 'whitespace-normal',
              cell: (item) => (
                <>
                  <span className="block truncate" title={item.name}>
                    {item.name}
                  </span>
                </>
              ),
            },
            {
              id: '类型',
              header: '类型',
              className: 'whitespace-normal',
              cell: (item) => <> {storageCategoryLabels[item.category]} </>,
            },
            {
              id: '对象数',
              header: '对象数',
              className: 'text-right tabular-nums whitespace-normal',
              cell: (item) => <> {item.object_count} </>,
            },
            {
              id: '创建时间',
              header: '创建时间',
              className: 'tabular-nums whitespace-normal',
              cell: (item) => <> {formatStorageDate(item.created_at)} </>,
            },
            {
              id: '大小',
              header: '大小',
              className: 'text-right tabular-nums whitespace-normal',
              cell: (item) => <> {formatStorageSize(item.size_bytes)} </>,
            },
            {
              id: '操作',
              header: '操作',
              className: 'text-right whitespace-normal',
              cell: (item) => (
                <>
                  <Button
                    aria-label={`删除文件 ${item.name}`}
                    onClick={() => onDelete(item)}
                    size="icon-lg"
                    type="button"
                    variant="ghost"
                  >
                    <Trash aria-hidden />
                  </Button>
                </>
              ),
            },
          ]}
        />
      </div>
    </BulkDeleteSelection>
  );
}
