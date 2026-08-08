import type { MindMapNode } from '@/types/video';
import { formatMilliseconds } from '@/utils/format';

export default function MindMapTree({ root }: { root: MindMapNode }) {
  return (
    <div className="overflow-hidden rounded-md border">
      <TreeNode depth={0} node={root} />
    </div>
  );
}

function TreeNode({ depth, node }: { depth: number; node: MindMapNode }) {
  return (
    <div>
      <div
        className="grid grid-cols-[auto_1fr_auto] gap-3 border-b px-4 py-3 last:border-b-0"
        style={{ paddingInlineStart: `${16 + depth * 22}px` }}
      >
        <CircleIcon className="mt-1 size-2 text-brand" weight="fill" />
        <span>
          <strong className="text-sm">{node.title}</strong>
          {node.summary ? (
            <small className="mt-1 block leading-5 text-muted-foreground">
              {node.summary}
            </small>
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

import { CircleIcon } from '@phosphor-icons/react';
