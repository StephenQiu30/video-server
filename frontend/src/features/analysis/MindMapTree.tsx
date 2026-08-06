import styles from './mind-map.module.css';
import type { MindMapNode } from './types';

type MindMapTreeProps = {
  root: MindMapNode;
};

export default function MindMapTree({ root }: MindMapTreeProps) {
  return (
    <div className={styles.mindMap}>
      <ul className={styles.mindMapRoot}>
        <MindMapBranch node={root} />
      </ul>
    </div>
  );
}

function MindMapBranch({ node }: { node: MindMapNode }) {
  return (
    <li>
      <article className={styles.mindMapNode}>
        <div className={styles.nodeHeading}>
          <strong>{node.title}</strong>
          {node.start_ms === null ? null : (
            <span>{formatTime(node.start_ms)}</span>
          )}
        </div>
        {node.summary ? <p>{node.summary}</p> : null}
      </article>
      {node.children.length > 0 ? (
        <ul>
          {node.children.map((child) => (
            <MindMapBranch key={child.id} node={child} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function formatTime(milliseconds: number): string {
  const totalSeconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(totalSeconds % 60).padStart(2, '0');
  return `${minutes}:${seconds}`;
}
