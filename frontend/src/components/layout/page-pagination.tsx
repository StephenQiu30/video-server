import { CaretLeft, CaretRight } from '@phosphor-icons/react';

import { Button } from '@/components/ui/button';
import {
  Pagination,
  PaginationContent,
  PaginationItem,
} from '@/components/ui/pagination';
import { cn } from '@/lib/utils';

type PagePaginationProps = {
  ariaLabel: string;
  className?: string;
  compact?: boolean;
  onPageChange: (page: number) => void;
  page: number;
  pages: number;
};

export function PagePagination({
  ariaLabel,
  className,
  compact = false,
  onPageChange,
  page,
  pages,
}: PagePaginationProps) {
  return (
    <Pagination aria-label={ariaLabel} className={className}>
      <PaginationContent>
        <PaginationItem>
          <Button
            aria-label="上一页"
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
            size={compact ? 'icon-lg' : 'lg'}
            type="button"
            variant={compact ? 'outline' : 'ghost'}
          >
            <CaretLeft aria-hidden />
            {compact ? null : <span className="hidden sm:inline">上一页</span>}
          </Button>
        </PaginationItem>
        <PaginationItem>
          <span
            aria-current="page"
            aria-live="polite"
            className={cn(
              'flex min-w-20 items-center justify-center font-normal text-muted-foreground tabular-nums',
              compact ? 'h-7 bg-background' : 'h-11 text-sm',
            )}
          >
            {page} / {pages}
          </span>
        </PaginationItem>
        <PaginationItem>
          <Button
            aria-label="下一页"
            disabled={page >= pages}
            onClick={() => onPageChange(page + 1)}
            size={compact ? 'icon-lg' : 'lg'}
            type="button"
            variant={compact ? 'outline' : 'ghost'}
          >
            {compact ? null : <span className="hidden sm:inline">下一页</span>}
            <CaretRight aria-hidden />
          </Button>
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  );
}
