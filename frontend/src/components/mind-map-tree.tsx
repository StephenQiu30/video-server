import { CaretRight } from '@phosphor-icons/react/dist/ssr';

import { cn } from '@/lib/utils';
import type { MindMapNode } from '@/types/video';
import { formatMilliseconds } from '@/utils/format';

export default function MindMapTree({
  className,
  root,
}: {
  className?: string;
  root: MindMapNode;
}) {
  return (
    <div className={cn('border-y', className)}>
      <TreeNode depth={0} node={root} />
    </div>
  );
}

function TreeNode({ depth, node }: { depth: number; node: MindMapNode }) {
  return (
    <div>
      <div
        className="grid grid-cols-[18px_1fr_auto] gap-2 border-b py-3 last:border-0"
        style={{ paddingInlineStart: `${Math.min(depth, 5) * 18}px` }}
      >
        <CaretRight
          aria-hidden
          className="mt-0.5 text-muted-foreground"
          size={15}
        />
        <span>
          <strong className="block text-sm">{node.title}</strong>
          {node.summary ? (
            <span className="mt-1 block text-sm leading-6 text-muted-foreground">
              {node.summary}
            </span>
          ) : null}
        </span>
        {node.start_ms === null ? null : (
          <span className="font-mono text-xs text-muted-foreground">
            {formatMilliseconds(node.start_ms)}
          </span>
        )}
      </div>
      {node.children.map((child) => (
        <TreeNode depth={depth + 1} key={child.id} node={child} />
      ))}
    </div>
  );
}
