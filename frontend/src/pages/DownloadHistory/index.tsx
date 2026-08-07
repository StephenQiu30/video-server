import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history } from '@umijs/max';
import { Alert, Button, Empty, Flex, Grid, Input, Select } from 'antd';
import { useState } from 'react';

import {
  displayError,
  issueDownloadUrl,
  triggerBrowserDownload,
} from '@/services/download';
import type { DownloadHistoryItem, DownloadStatus } from '@/types/video';
import { historyColumns, statusOptions } from './components';
import { useDownloadHistory } from './hooks';

export default function DownloadHistoryPage() {
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<DownloadStatus | undefined>();
  const [downloadId, setDownloadId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const screens = Grid.useBreakpoint();
  const pageSize = 20;
  const state = useDownloadHistory({
    page,
    page_size: pageSize,
    search: search || undefined,
    status,
  });

  function applySearch(value = searchInput) {
    setPage(1);
    setSearch(value.trim());
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

  const columns = historyColumns({ downloadId, onDownload: handleDownload });

  return (
    <PageContainer
      content="查看、筛选并继续处理已创建的下载任务。"
      extra={[
        <Button
          icon={<PlusOutlined />}
          key="new"
          onClick={() => history.push('/')}
          type="primary"
        >
          新建下载
        </Button>,
      ]}
      title="下载历史"
    >
      <Flex gap={16} vertical>
        {actionError ? (
          <Alert
            action={
              <Button onClick={() => setActionError(null)}>知道了</Button>
            }
            showIcon
            title={actionError}
            type="info"
          />
        ) : null}
        {state.error ? (
          <Alert
            action={
              <Button icon={<ReloadOutlined />} onClick={state.retry}>
                重试
              </Button>
            }
            showIcon
            title={state.error}
            type="info"
          />
        ) : null}

        <ProTable<DownloadHistoryItem>
          columns={columns}
          dataSource={state.data?.items ?? []}
          headerTitle="下载记录"
          loading={state.loading && !state.data}
          locale={{
            emptyText: (
              <Empty
                description={
                  search || status ? '没有匹配的下载记录' : '还没有下载记录'
                }
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <Button onClick={() => history.push('/')} type="primary">
                  新建下载
                </Button>
              </Empty>
            ),
          }}
          options={false}
          pagination={
            state.data && state.data.total > 0
              ? {
                  current: state.data.page,
                  onChange: setPage,
                  pageSize: state.data.page_size,
                  showSizeChanger: false,
                  total: state.data.total,
                }
              : false
          }
          rowKey="id"
          scroll={{ x: 900 }}
          search={false}
          toolBarRender={() => [
            <Flex
              gap={8}
              key="filters"
              style={{ width: screens.sm ? undefined : '100%' }}
              vertical={!screens.sm}
              wrap={screens.sm}
            >
              <Input.Search
                allowClear
                aria-label="搜索下载历史"
                onChange={(event) => setSearchInput(event.target.value)}
                onSearch={applySearch}
                placeholder="按视频标题搜索"
                style={{ width: screens.sm ? 280 : '100%' }}
                value={searchInput}
              />
              <Select
                aria-label="按状态筛选"
                onChange={applyStatus}
                options={statusOptions}
                style={{ width: screens.sm ? 128 : '100%' }}
                value={status ?? ''}
              />
              <Button
                block={!screens.sm}
                icon={<ReloadOutlined />}
                onClick={state.retry}
              >
                刷新
              </Button>
            </Flex>,
          ]}
        />
      </Flex>
    </PageContainer>
  );
}
