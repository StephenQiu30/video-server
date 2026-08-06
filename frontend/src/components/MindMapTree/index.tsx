import { Tree, type TreeDataNode } from 'antd';

import type { MindMapNode } from '@/types/video';
import { formatMilliseconds } from '@/utils/format';

import styles from './index.module.css';

type MindMapTreeProps = {
  root: MindMapNode;
};

export default function MindMapTree({ root }: MindMapTreeProps) {
  return (
    <div className={styles.mindMap}>
      <Tree
        blockNode
        defaultExpandAll
        selectable={false}
        showLine
        treeData={[toTreeNode(root)]}
      />
    </div>
  );
}

function toTreeNode(node: MindMapNode): TreeDataNode {
  return {
    key: node.id,
    title: (
      <div className={styles.node}>
        <strong>{node.title}</strong>
        {node.start_ms === null ? null : (
          <span>{formatMilliseconds(node.start_ms)}</span>
        )}
        {node.summary ? <small>{node.summary}</small> : null}
      </div>
    ),
    children: node.children.map(toTreeNode),
  };
}
