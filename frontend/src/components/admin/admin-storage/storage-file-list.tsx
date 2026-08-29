import { Fragment } from 'react';

import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemSeparator,
  ItemTitle,
} from '@/components/ui/item';

import {
  formatStorageDate,
  formatStorageSize,
  storageCategoryLabels,
} from './model';

export function StorageFileList({
  items,
}: {
  items: API.StoredFileResponse[];
}) {
  return (
    <ItemGroup aria-label="持久文件列表" className="hairline gap-0 border-y">
      {items.map((item, index) => (
        <Fragment key={`${item.category}-${item.id}`}>
          <Item className="rounded-none border-0 px-0 py-5" role="listitem">
            <ItemContent className="min-w-0">
              <ItemTitle className="w-full min-w-0 line-clamp-none">
                <span
                  className="block w-full min-w-0 truncate"
                  title={item.name}
                >
                  {item.name}
                </span>
              </ItemTitle>
              <ItemDescription className="line-clamp-none">
                {storageCategoryLabels[item.category]} · {item.object_count}{' '}
                个对象 · {formatStorageDate(item.created_at)}
              </ItemDescription>
            </ItemContent>
            <ItemActions className="text-sm font-medium tabular-nums">
              {formatStorageSize(item.size_bytes)}
            </ItemActions>
          </Item>
          {index < items.length - 1 ? (
            <ItemSeparator className="hairline my-0" />
          ) : null}
        </Fragment>
      ))}
    </ItemGroup>
  );
}
