import { CaretRightFilled } from '@ant-design/icons';
import { Typography } from 'antd';

import type { MindMapNode } from '@/types/video';
import { formatMilliseconds } from '@/utils/format';

export default function MindMapTree({ root }: { root: MindMapNode }) {
  return (
    <div className="mind-map">
      <TreeNode depth={0} node={root} />
    </div>
  );
}

function TreeNode({ depth, node }: { depth: number; node: MindMapNode }) {
  return (
    <div>
      <div
        className="mind-map-node"
        style={{ paddingInlineStart: `${16 + depth * 22}px` }}
      >
        <CaretRightFilled className="mind-map-dot" />
        <span>
          <Typography.Text strong>{node.title}</Typography.Text>
          {node.summary ? (
            <Typography.Paragraph type="secondary">
              {node.summary}
            </Typography.Paragraph>
          ) : null}
        </span>
        {node.start_ms === null ? null : (
          <Typography.Text code>
            {formatMilliseconds(node.start_ms)}
          </Typography.Text>
        )}
      </div>
      {node.children.map((child) => (
        <TreeNode depth={depth + 1} key={child.id} node={child} />
      ))}
    </div>
  );
}
