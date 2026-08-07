import {
  DownloadOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { PageContainer, ProCard } from '@ant-design/pro-components';
import { history } from '@umijs/max';
import {
  Alert,
  Button,
  Empty,
  Flex,
  Input,
  Pagination,
  Select,
  Typography,
} from 'antd';
import { useState } from 'react';

import {
  displayError,
  issueDownloadUrl,
  triggerBrowserDownload,
} from '@/services/download';
import type { DownloadHistoryItem, DownloadStatus } from '@/types/video';
import { HistoryItem, HistorySkeleton, StatCard } from './components';
import { useDownloadHistory } from './hooks';
import styles from './index.module.css';

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '排队中', value: 'queued' },
  { label: '下载中', value: 'running' },
  { label: '等待重试', value: 'retry_wait' },
  { label: '已完成', value: 'succeeded' },
  { label: '失败', value: 'failed' },
  { label: '已取消', value: 'cancelled' },
];

export default function DownloadHistoryPage() {
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<DownloadStatus | undefined>();
  const [downloadId, setDownloadId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const pageSize = 20;
  const state = useDownloadHistory({
    page,
    page_size: pageSize,
    search: search || undefined,
    status,
  });
  const summary = state.data?.summary;

  function applySearch() {
    setPage(1);
    setSearch(searchInput.trim());
  }

  function applyStatus(value: string) {
    setPage(1);
    setStatus((value || undefined) as DownloadStatus | undefined);
  }

  async function handleDownload(item: DownloadHistoryItem) {
    setDownloadId(item.id);
    setActionError(null);
    try {
      const result = await issueDownloadUrl(item.id);
      triggerBrowserDownload(result.url);
    } catch (reason) {
      setActionError(displayError(reason));
    } finally {
      setDownloadId(null);
    }
  }

  return (
    <PageContainer className={styles.container} ghost title={false}>
      <main className={styles.page}>
        <header className={styles.masthead}>
          <div>
            <Typography.Text className={styles.eyebrow}>
              DOWNLOAD ARCHIVE
            </Typography.Text>
            <Typography.Title level={1}>下载历史</Typography.Title>
            <Typography.Paragraph>
              每一次解析和下载，都会在这里留下可回到的记录。
            </Typography.Paragraph>
          </div>
          <Button
            className={styles.newButton}
            icon={<DownloadOutlined />}
            onClick={() => history.push('/')}
            type="primary"
          >
            新建下载
          </Button>
        </header>

        {summary ? (
          <section aria-label="下载统计" className={styles.summaryGrid}>
            <StatCard label="全部记录" value={summary.total} />
            <StatCard label="已完成" value={summary.succeeded} tone="success" />
            <StatCard label="处理中" value={summary.active} tone="active" />
            <StatCard label="失败" value={summary.failed} tone="error" />
          </section>
        ) : null}

          <ProCard className={styles.toolbar} variant="outlined">
            <Flex gap={12} justify="space-between" wrap>
            <Input.Search
              allowClear
              aria-label="搜索下载历史"
              enterButton={<SearchOutlined />}
              onChange={(event) => setSearchInput(event.target.value)}
              onSearch={applySearch}
              placeholder="按视频标题搜索"
              value={searchInput}
            />
            <Select
              aria-label="按状态筛选"
              onChange={applyStatus}
              options={statusOptions}
              value={status ?? ''}
            />
          </Flex>
          </ProCard>

        {actionError ? (
          <Alert
            action={
              <Button onClick={() => setActionError(null)}>知道了</Button>
            }
            className={styles.alert}
            showIcon
            title={actionError}
            type="warning"
          />
        ) : null}
        {state.error ? (
          <Alert
            action={
              <Button icon={<ReloadOutlined />} onClick={state.retry}>
                重试
              </Button>
            }
            className={styles.alert}
            showIcon
            title={state.error}
            type="error"
          />
        ) : null}

        <section aria-label="下载记录" className={styles.records}>
          {state.loading && !state.data ? <HistorySkeleton /> : null}
          {!state.loading && state.data?.items.length === 0 ? (
            <Empty
              className={styles.empty}
              description={
                search || status ? '没有匹配的下载记录' : '还没有下载记录'
              }
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
              <Button onClick={() => history.push('/')} type="primary">
                新建下载
              </Button>
            </Empty>
          ) : null}
          {state.data?.items.map((item) => (
            <HistoryItem
              item={item}
              key={item.id}
              loading={downloadId === item.id}
              onDownload={handleDownload}
            />
          ))}
        </section>

        {state.data && state.data.total > 0 ? (
          <Pagination
            align="center"
            current={state.data.page}
            pageSize={state.data.page_size}
            showSizeChanger={false}
            total={state.data.total}
            onChange={setPage}
          />
        ) : null}
      </main>
    </PageContainer>
  );
}
