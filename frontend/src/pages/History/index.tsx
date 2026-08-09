import { PlusOutlined } from '@ant-design/icons';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { useNavigate } from '@umijs/max';
import { Alert, Button, Typography } from 'antd';
import { useCallback, useMemo, useState } from 'react';

import {
  displayError,
  getDownloadHistory,
  issueDownloadUrl,
  triggerBrowserDownload,
} from '@/services/download';
import type { DownloadHistoryItem, DownloadStatus } from '@/types/video';
import { createHistoryColumns } from './columns';
import './index.less';

type HistorySearchParams = {
  search?: string;
  status?: DownloadStatus;
};

export default function HistoryPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const download = useCallback(async (item: DownloadHistoryItem) => {
    setError(null);
    try {
      triggerBrowserDownload((await issueDownloadUrl(item.id)).url);
    } catch (reason) {
      setError(displayError(reason));
    }
  }, []);

  const navigateToItem = useCallback(
    (id: string) => {
      navigate(`/downloads/${encodeURIComponent(id)}`);
    },
    [navigate],
  );

  const columns = useMemo(
    () =>
      createHistoryColumns({
        onDownload: (item) => void download(item),
        onOpen: navigateToItem,
      }),
    [download, navigateToItem],
  );

  return (
    <PageContainer className="history-page" title={false}>
      <div className="page-heading-row">
        <div>
          <p className="page-eyebrow">Download history</p>
          <Typography.Title
            className="page-title"
            level={1}
            style={{ marginBlock: 4 }}
          >
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

      {error ? (
        <Alert
          className="history-alert"
          description={error}
          title="操作未完成"
          showIcon
          type="error"
        />
      ) : null}

      <ProTable<DownloadHistoryItem, HistorySearchParams>
        cardBordered={false}
        columns={columns}
        locale={{ emptyText: '没有匹配的下载记录' }}
        onLoad={() => setError(null)}
        onRequestError={(reason) => setError(displayError(reason))}
        options={{ density: false, fullScreen: false, setting: false }}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: false,
          showTotal: (total) => `共 ${total} 条`,
        }}
        request={async ({ current = 1, pageSize = 20, search, status }) => {
          const result = await getDownloadHistory({
            page: current,
            page_size: pageSize,
            search: search?.trim() || undefined,
            status,
          });
          return {
            data: result.items,
            success: true,
            total: result.total,
          };
        }}
        rowKey="id"
        search={{
          collapseRender: false,
          defaultCollapsed: false,
          labelWidth: 'auto',
          resetText: '重置',
          searchText: '查询',
          span: { xs: 24, sm: 12, md: 12, lg: 8, xl: 8, xxl: 6 },
        }}
        scroll={{ x: 900 }}
      />
    </PageContainer>
  );
}
