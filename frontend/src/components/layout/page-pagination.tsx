import { CaretLeft, CaretRight } from '@phosphor-icons/react';
import { cn } from 'cn';
import { Button } from '@/components/ui/button';
import {
  Pagination,
  PaginationContent,
  PaginationItem,
} from '@/components/ui/pagination';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export const DEFAULT_PAGE_SIZE = 10;
export const PAGE_SIZE_OPTIONS = [10, 20, 50] as const;

type PagePaginationProps = {
  ariaLabel: string;
  className?: string;
  onPageChange: (page: number) => void;
  page: number;
  pages?: number;
  hasNext?: boolean;
  busy?: boolean;
  pageSize: number;
  onPageSizeChange: (size: number) => void;
};

export function PagePagination({
  ariaLabel,
  className,
  onPageChange,
  page,
  pages,
  hasNext,
  busy = false,
  pageSize,
  onPageSizeChange,
}: PagePaginationProps) {
  return (
    <div
      className={cn(
        'ml-auto flex w-full flex-wrap items-center justify-end gap-3',
        className,
      )}
    >
      <Select
        disabled={busy}
        value={String(pageSize)}
        onValueChange={(value) => onPageSizeChange(Number(value))}
      >
        <SelectTrigger aria-label={`${ariaLabel}每页条数`}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            {PAGE_SIZE_OPTIONS.map((size) => (
              <SelectItem key={size} value={String(size)}>
                每页 {size} 条
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
      <Pagination aria-label={ariaLabel} className="mx-0 w-auto justify-end">
        <PaginationContent>
          <PaginationItem>
            <Button
              aria-label="上一页"
              disabled={busy || page <= 1}
              onClick={() => onPageChange(page - 1)}
              size="icon"
              type="button"
              variant="outline"
            >
              <CaretLeft aria-hidden />
            </Button>
          </PaginationItem>
          <PaginationItem>
            <span
              aria-current="page"
              aria-live="polite"
              className="px-2 text-sm tabular-nums"
            >
              {pages === undefined
                ? `第 ${page} 页`
                : `${page} / ${Math.max(1, pages)}`}
            </span>
          </PaginationItem>
          {pages === undefined
            ? Array.from(
                { length: page + Number(hasNext) },
                (_, index) => index + 1,
              )
                .filter((value) => value === 1 || Math.abs(value - page) <= 1)
                .map((value) => (
                  <PaginationItem key={value}>
                    <Button
                      aria-label={`第 ${value} 页`}
                      aria-current={value === page ? 'page' : undefined}
                      disabled={busy}
                      onClick={() => onPageChange(value)}
                      size="icon"
                      variant={value === page ? 'outline' : 'ghost'}
                    >
                      {value}
                    </Button>
                  </PaginationItem>
                ))
            : null}
          <PaginationItem>
            <Button
              aria-label="下一页"
              disabled={
                busy || (pages === undefined ? !hasNext : page >= pages)
              }
              onClick={() => onPageChange(page + 1)}
              size="icon"
              type="button"
              variant="outline"
            >
              <CaretRight aria-hidden />
            </Button>
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    </div>
  );
}
