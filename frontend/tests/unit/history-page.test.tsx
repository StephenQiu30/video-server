import { render } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import HistoryPage from '@/pages/History';
import type {
  DownloadHistory,
  DownloadHistoryItem,
  DownloadStatus,
} from '@/types/video';

const runtime = vi.hoisted(() => ({
  getDownloadHistory: vi.fn(),
  issueDownloadUrl: vi.fn(),
  navigate: vi.fn(),
  tableProps: undefined as unknown,
  triggerBrowserDownload: vi.fn(),
}));

vi.mock('@ant-design/pro-components', () => ({
  PageContainer: ({ children }: { children: ReactNode }) => <>{children}</>,
  ProTable: (props: unknown) => {
    runtime.tableProps = props;
    return <div data-testid="history-table" />;
  },
}));

vi.mock('@umijs/max', () => ({
  useNavigate: () => runtime.navigate,
}));

vi.mock('@/services/download', () => ({
  displayError: () => '请求失败',
  getDownloadHistory: runtime.getDownloadHistory,
  issueDownloadUrl: runtime.issueDownloadUrl,
  triggerBrowserDownload: runtime.triggerBrowserDownload,
}));

type CapturedColumn = {
  dataIndex?: string;
  fieldProps?: Record<string, unknown>;
  hideInTable?: boolean;
  search?: boolean;
  valueEnum?: Record<string, { text: string }>;
  valueType?: string;
};

type CapturedTableProps = {
  columns: CapturedColumn[];
  options: Record<string, boolean>;
  pagination: {
    defaultPageSize: number;
    showSizeChanger: boolean;
  };
  request: (params: {
    current?: number;
    pageSize?: number;
    search?: string;
    status?: DownloadStatus;
  }) => Promise<{
    data: DownloadHistoryItem[];
    success: boolean;
    total: number;
  }>;
  search: Record<string, unknown>;
};

describe('HistoryPage', () => {
  beforeEach(() => {
    runtime.getDownloadHistory.mockReset();
    runtime.tableProps = undefined;
  });

  it('uses ProColumns as the single source of search fields', () => {
    render(<HistoryPage />);

    const props = runtime.tableProps as CapturedTableProps;
    const titleSearch = props.columns.find(
      (column) => column.dataIndex === 'search',
    );
    const statusSearch = props.columns.find(
      (column) => column.dataIndex === 'status',
    );

    expect(titleSearch).toMatchObject({
      hideInTable: true,
      valueType: 'text',
    });
    expect(statusSearch).toMatchObject({
      valueType: 'select',
      valueEnum: {
        queued: { text: '排队中' },
        succeeded: { text: '已完成' },
        failed: { text: '失败' },
      },
    });
    expect(
      props.columns
        .filter((column) =>
          ['title', 'format_name', 'created_at'].includes(
            column.dataIndex ?? '',
          ),
        )
        .every((column) => column.search === false),
    ).toBe(true);
    expect(props.pagination).toMatchObject({
      defaultPageSize: 20,
      showSizeChanger: false,
    });
    expect(props.options).toMatchObject({
      density: false,
      fullScreen: false,
      setting: false,
    });
  });

  it('maps native ProTable request parameters to the history API', async () => {
    const response: DownloadHistory = {
      items: [],
      page: 3,
      page_size: 20,
      total: 41,
      summary: { total: 41, succeeded: 10, active: 1, failed: 2 },
    };
    runtime.getDownloadHistory.mockResolvedValue(response);
    render(<HistoryPage />);

    const props = runtime.tableProps as CapturedTableProps;
    const result = await props.request({
      current: 3,
      pageSize: 20,
      search: '  示例视频  ',
      status: 'succeeded',
    });

    expect(runtime.getDownloadHistory).toHaveBeenCalledWith({
      page: 3,
      page_size: 20,
      search: '示例视频',
      status: 'succeeded',
    });
    expect(result).toEqual({ data: [], success: true, total: 41 });
  });
});
