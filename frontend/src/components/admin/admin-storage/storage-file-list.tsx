import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
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
    <ItemGroup aria-label="持久文件列表" className="gap-2">
      {items.map((item) => (
        <Item
          className="rounded-md border-0 px-3 py-5 hover:bg-muted/50"
          key={`${item.category}-${item.id}`}
          role="listitem"
        >
          <ItemContent className="min-w-0">
            <ItemTitle className="w-full min-w-0 line-clamp-none">
              <span className="block w-full min-w-0 truncate" title={item.name}>
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
      ))}
    </ItemGroup>
  );
}
