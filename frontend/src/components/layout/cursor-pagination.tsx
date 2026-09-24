import { CaretLeft, CaretRight } from '@phosphor-icons/react';
import { Fragment } from 'react';
import { Button } from '@/components/ui/button';
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
} from '@/components/ui/pagination';

export function CursorPagination({
  ariaLabel,
  page,
  hasNext,
  busy = false,
  onPageChange,
}: {
  ariaLabel: string;
  page: number;
  hasNext: boolean;
  busy?: boolean;
  onPageChange: (page: number) => void;
}) {
  const lastKnownPage = page + Number(hasNext);
  const nearbyPages = Array.from(
    { length: lastKnownPage - Math.max(1, page - 2) + 1 },
    (_, index) => Math.max(1, page - 2) + index,
  );
  const pages = page > 3 ? [1, ...nearbyPages] : nearbyPages;

  return (
    <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
      <span className="text-sm text-muted-foreground tabular-nums">
        第 {page} 页
      </span>
      <Pagination aria-label={ariaLabel} className="mx-0 w-auto justify-end">
        <PaginationContent>
          <PaginationItem>
            <Button
              aria-label="上一页"
              disabled={busy || page <= 1}
              onClick={() => onPageChange(page - 1)}
              size="icon"
              type="button"
              variant="ghost"
            >
              <CaretLeft aria-hidden />
            </Button>
          </PaginationItem>
          {pages.map((number, index) => (
            <Fragment key={number}>
              {index === 1 && number > 2 ? (
                <PaginationItem>
                  <PaginationEllipsis />
                </PaginationItem>
              ) : null}
              <PaginationItem>
                <Button
                  aria-current={number === page ? 'page' : undefined}
                  aria-label={`第 ${number} 页`}
                  disabled={busy}
                  onClick={() => onPageChange(number)}
                  size="icon"
                  type="button"
                  variant={number === page ? 'outline' : 'ghost'}
                >
                  {number}
                </Button>
              </PaginationItem>
            </Fragment>
          ))}
          <PaginationItem>
            <Button
              aria-label="下一页"
              disabled={busy || !hasNext}
              onClick={() => onPageChange(page + 1)}
              size="icon"
              type="button"
              variant="ghost"
            >
              <CaretRight aria-hidden />
            </Button>
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    </div>
  );
}
