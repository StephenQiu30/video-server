import { Tag } from 'antd';

const stateMap: Record<API.Task['state'], { color: string; label: string }> = {
  queued: { color: 'blue', label: '排队中' },
  running: { color: 'processing', label: '下载中' },
  succeeded: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
  canceled: { color: 'default', label: '已取消' },
};

export function TaskStateTag({ state }: { state: API.Task['state'] }) {
  const item = stateMap[state] || { color: 'default', label: state };
  return (
    <Tag className="status-pill" color={item.color}>
      {item.label}
    </Tag>
  );
}
