import {
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { useNavigate } from '@umijs/max';
import {
  Alert,
  Button,
  Flex,
  Input,
  Pagination,
  Select,
  Typography,
} from 'antd';
import { useState } from 'react';

import HistoryTable from './components/HistoryTable';
import { useDownloadHistory } from '@/hooks/useDownloadHistory';
import { displayError, issueDownloadUrl, triggerBrowserDownload } from '@/services/download';
import type { DownloadHistoryItem, DownloadStatus } from '@/types/video';
import './index.less';

export default function HistoryPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<DownloadStatus | undefined>();
  const [actionError, setActionError] = useState<string | null>(null);
  const state = useDownloadHistory({
    page,
    page_size: 20,
    search: search || undefined,
    status,
  });

  async function download(item: DownloadHistoryItem) {
    setActionError(null);
    try {
      triggerBrowserDownload((await issueDownloadUrl(item.id)).url);
    } catch (reason) {
      setActionError(displayError(reason));
    }
  }

  return (
    <PageContainer className="history-page" title={false}>
      <div className="page-heading-row">
        <div>
          <p className="page-eyebrow">Download history</p>
          <Typography.Title className="page-title" level={1} style={{ marginBlock: 4 }}>
            下载历史
          </Typography.Title>
          <Typography.Paragraph className="page-description">
            继续查看、获取或分析已创建的任务。
          </Typography.Paragraph>
        </div>
        <Button
          icon={<PlusOutlined />}
          onClick={() => navigate('/')}
          type="primary"
        >
          新建下载
        </Button>
      </div>

      <div className="history-toolbar">
        <Flex gap={12} wrap>
          <Input.Search
            aria-label="搜索下载历史"
            onChange={(event) => setSearchInput(event.target.value)}
            onSearch={() => {
              setPage(1);
              setSearch(searchInput.trim());
            }}
            placeholder="按视频标题搜索"
            prefix={<SearchOutlined />}
            style={{ flex: '1 1 280px' }}
            value={searchInput}
          />
          <Select
            aria-label="按状态筛选"
            onChange={(value) => {
              setPage(1);
              setStatus(value === 'all' ? undefined : (value as DownloadStatus));
            }}
            options={[
              { label: '全部状态', value: 'all' },
              ...Object.entries(statusLabels).map(([value, label]) => ({
                label,
                value: value as DownloadStatus,
              })),
            ]}
            style={{ minWidth: 150 }}
            value={status ?? 'all'}
          />
          <Button icon={<ReloadOutlined />} onClick={state.retry}>
            刷新
          </Button>
        </Flex>
      </div>

      {state.error || actionError ? (
        <Alert
          className="history-alert"
          description={state.error ?? actionError}
          title="操作未完成"
          showIcon
          type="error"
        />
      ) : null}

      <HistoryTable
        data={state.data}
        loading={state.loading}
        onDownload={download}
        onOpen={(id) => navigate(`/downloads/${encodeURIComponent(id)}`)}
      />

      {state.data && state.data.total > state.data.page_size ? (
        <Flex justify="flex-end" style={{ marginTop: 20 }}>
          <Pagination
            current={page}
            onChange={setPage}
            pageSize={state.data.page_size}
            showSizeChanger={false}
            total={state.data.total}
          />
        </Flex>
      ) : null}
    </PageContainer>
  );
}

const statusLabels: Record<DownloadStatus, string> = {
  queued: '排队中',
  running: '下载中',
  retry_wait: '等待重试',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已取消',
};
