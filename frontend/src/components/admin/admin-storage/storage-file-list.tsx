import { File, FileText, FilmStrip } from '@phosphor-icons/react';

import { Badge } from '@/components/ui/badge';

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
    <ul className="divide-y divide-border border-y" aria-label="持久文件列表">
      {items.map((item) => {
        const Icon = categoryIcon(item.category);
        return (
          <li
            className="grid gap-4 py-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"
            key={`${item.category}-${item.id}`}
          >
            <div className="flex min-w-0 items-start gap-3">
              <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                <Icon aria-hidden className="size-5" />
              </span>
              <div className="min-w-0">
                <p className="truncate font-medium" title={item.name}>
                  {item.name}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                  <Badge variant="neutral">
                    {storageCategoryLabels[item.category]}
                  </Badge>
                  <span>{item.object_count} 个对象</span>
                  <span>{formatStorageDate(item.created_at)}</span>
                </div>
              </div>
            </div>
            <span className="pl-12 text-sm font-medium tabular-nums sm:pl-0">
              {formatStorageSize(item.size_bytes)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function categoryIcon(category: API.StoredFileCategory) {
  if (category === 'video') return FilmStrip;
  if (category === 'screenplay') return FileText;
  return File;
}
