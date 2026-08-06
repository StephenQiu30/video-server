import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { rootContainer } from '@/app';
import LegalNotice from '@/components/LegalNotice';
import NotFoundPage from '@/pages/404';
import DownloadPage from '@/pages/Download';
import FormatList from '@/pages/Download/components/FormatList';
import MediaSummary from '@/pages/Download/components/MediaSummary';
import { useInspectFlow } from '@/pages/Download/hooks';
import DownloadJobPage from '@/pages/DownloadJob';
import { useDownloadJob, useDownloadUrl } from '@/pages/DownloadJob/hooks';

const navigate = vi.fn();
let routeParams: { jobId?: string } = { jobId: 'job-12345678' };
vi.mock('react-router-dom', () => ({
  useNavigate: () => navigate,
  useParams: () => routeParams,
}));

vi.mock('@/pages/Download/hooks', () => ({ useInspectFlow: vi.fn() }));
vi.mock('@/pages/DownloadJob/hooks', () => ({
  useDownloadJob: vi.fn(),
  useDownloadUrl: vi.fn(),
  openDownloadUrl: vi.fn(),
}));

const useInspectFlowMock = vi.mocked(useInspectFlow);
const useDownloadJobMock = vi.mocked(useDownloadJob);
const useDownloadUrlMock = vi.mocked(useDownloadUrl);

const media = {
  id: 'source-1',
  title: '<不可信标题>',
  platform: 'example',
  thumbnailUrl: null,
  durationSeconds: 90,
  expiresAt: new Date(Date.now() + 60_000).toISOString(),
  formats: [
    {
      id: 'format-1',
      label: '720p',
      width: 1280,
      height: 720,
      fps: 30,
      container: 'mp4',
      videoCodec: 'h264',
      audioCodec: 'aac',
      estimatedSizeBytes: 1024,
      requiresMerge: true,
    },
  ],
};

function inspectState(overrides: Record<string, unknown> = {}) {
  return {
    state: 'idle',
    media: null,
    selectedFormatId: null,
    setSelectedFormatId: vi.fn(),
    problem: null,
    createProblem: null,
    inspect: vi.fn().mockResolvedValue(null),
    createDownload: vi.fn().mockResolvedValue('job-1'),
    isInspecting: false,
    isCreating: false,
    ...overrides,
  } as ReturnType<typeof useInspectFlow>;
}

function jobState(overrides: Record<string, unknown> = {}) {
  return {
    data: null,
    isLoading: false,
    isError: false,
    error: null,
    ...overrides,
  } as ReturnType<typeof useDownloadJob>;
}

function urlState(overrides: Record<string, unknown> = {}) {
  return {
    isPending: false,
    problem: null,
    request: vi.fn().mockResolvedValue({
      url: 'https://minio.example.test/file.mp4',
      expiresAt: new Date(Date.now() + 60_000).toISOString(),
    }),
    ...overrides,
  } as unknown as ReturnType<typeof useDownloadUrl>;
}

beforeEach(() => {
  vi.clearAllMocks();
  useInspectFlowMock.mockReturnValue(inspectState());
  useDownloadJobMock.mockReturnValue(jobState());
  useDownloadUrlMock.mockReturnValue(urlState());
  routeParams = { jobId: 'job-12345678' };
  Object.defineProperty(navigator, 'onLine', {
    configurable: true,
    value: true,
  });
});

describe('shared and route shell components', () => {
  it('renders legal notice and wraps content with Ant Design providers', () => {
    expect(
      render(<LegalNotice />).getByText(/仅下载你有权使用/),
    ).toBeInTheDocument();
    const child = <span>child content</span>;
    expect(
      render(rootContainer(child)).getByText('child content'),
    ).toBeInTheDocument();
  });

  it('renders the not-found recovery action', () => {
    render(<NotFoundPage />);
    fireEvent.click(screen.getByRole('button', { name: '返回下载' }));
    expect(navigate).toHaveBeenCalledWith('/download');
  });

  it('renders format metadata and summary safely', () => {
    const changed = vi.fn();
    render(
      <FormatList formats={media.formats} value={null} onChange={changed} />,
    );
    expect(screen.getByText('720p')).toBeInTheDocument();
    expect(screen.getByText('将自动合并音视频')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('radio', { name: /720p/ }));
    expect(changed).toHaveBeenCalledWith('format-1');
    render(<MediaSummary media={media} />);
    expect(screen.getByText('<不可信标题>')).toBeInTheDocument();
    expect(screen.getByText(/example · 1:30/)).toBeInTheDocument();
    render(
      <FormatList
        formats={[
          {
            ...media.formats[0],
            container: null,
            fps: null,
            requiresMerge: false,
          },
        ]}
        value={null}
        onChange={changed}
      />,
    );
    render(
      <MediaSummary
        media={{ ...media, thumbnailUrl: 'https://img.example.test/a.jpg' }}
      />,
    );
    expect(screen.getByAltText('视频缩略图')).toBeInTheDocument();
  });
});

describe('download page user flow', () => {
  it('validates empty input and submits one trimmed valid URL', async () => {
    const inspect = vi.fn().mockResolvedValue(null);
    useInspectFlowMock.mockReturnValue(inspectState({ inspect }));
    render(<DownloadPage />);
    const input = screen.getByRole('textbox', { name: '视频链接' });
    fireEvent.click(screen.getByRole('button', { name: /解析视频/ }));
    expect(screen.getByText('请输入视频链接')).toBeInTheDocument();
    fireEvent.change(input, {
      target: { value: '  https://example.test/video  ' },
    });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
    await waitFor(() =>
      expect(inspect).toHaveBeenCalledWith('https://example.test/video'),
    );
  });

  it('shows inspected formats and navigates after creating a job', async () => {
    const createDownload = vi.fn().mockResolvedValue('job-1');
    useInspectFlowMock.mockReturnValue(
      inspectState({
        state: 'inspected',
        media,
        selectedFormatId: 'format-1',
        createDownload,
      }),
    );
    render(<DownloadPage />);
    expect(
      screen.getByRole('heading', { name: '<不可信标题>' }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '开始下载' }));
    await waitFor(() =>
      expect(createDownload).toHaveBeenCalledWith(media.formats[0]),
    );
    expect(navigate).toHaveBeenCalledWith('/downloads/job-1');
  });

  it('shows inspect failure, expiry and creation errors with recovery actions', () => {
    const inspect = vi.fn();
    useInspectFlowMock.mockReturnValue(
      inspectState({
        state: 'inspect_failed',
        problem: { title: '解析失败', detail: '请稍后重试' },
        inspect,
      }),
    );
    render(<DownloadPage />);
    expect(screen.getByText('解析失败')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /重新解析/ }));
    expect(inspect).not.toHaveBeenCalled();
    useInspectFlowMock.mockReturnValue(
      inspectState({
        state: 'inspected',
        media,
        selectedFormatId: 'format-1',
        createProblem: { title: '创建失败', detail: '任务冲突' },
      }),
    );
    render(<DownloadPage />);
    expect(screen.getByText('创建失败')).toBeInTheDocument();
    useInspectFlowMock.mockReturnValue(inspectState({ state: 'expired' }));
    render(<DownloadPage />);
    expect(screen.getByText('解析结果已过期')).toBeInTheDocument();
  });
});

describe('download job page states and recovery', () => {
  it('renders loading, offline and query errors', () => {
    useDownloadJobMock.mockReturnValue(jobState({ isLoading: true }));
    render(<DownloadJobPage />);
    expect(screen.getByText('正在读取任务状态')).toBeInTheDocument();
    fireEvent(window, new Event('offline'));
    expect(screen.getByText('当前处于离线状态')).toBeInTheDocument();
    useDownloadJobMock.mockReturnValue(
      jobState({ isError: true, error: { status: 404 } }),
    );
    render(<DownloadJobPage />);
    expect(
      screen.getAllByText('请求未完成，请检查后重试').length,
    ).toBeGreaterThan(0);
    useDownloadJobMock.mockReturnValue(
      jobState({
        isError: true,
        data: {
          id: 'job-1',
          status: 'queued',
          stage: null,
          progressPercent: null,
          downloadedBytes: null,
          totalBytes: null,
          error: null,
          artifact: null,
          createdAt: null,
          updatedAt: null,
        },
        error: { status: 503 },
      }),
    );
    render(<DownloadJobPage />);
    expect(screen.getByText('状态刷新暂时失败')).toBeInTheDocument();
  });

  it.each([
    ['queued', '任务排队中'],
    ['running', '正在处理'],
    ['failed', '下载失败'],
    ['expired', '文件已过期'],
  ] as const)('renders %s status', (status, text) => {
    useDownloadJobMock.mockReturnValue(
      jobState({
        data: {
          id: 'job-1',
          status,
          stage: null,
          progressPercent: null,
          downloadedBytes: null,
          totalBytes: null,
          error: status === 'failed' ? { detail: '源不可用' } : null,
          artifact: null,
          createdAt: null,
          updatedAt: null,
        },
      }),
    );
    render(<DownloadJobPage />);
    expect(screen.getByText(text)).toBeInTheDocument();
  });

  it('renders a successful artifact and requests a temporary URL only on click', async () => {
    const request = vi.fn().mockResolvedValue({
      url: 'https://minio.example.test/file.mp4',
      expiresAt: new Date(Date.now() + 60_000).toISOString(),
    });
    useDownloadJobMock.mockReturnValue(
      jobState({
        data: {
          id: 'job-1',
          status: 'succeeded',
          stage: null,
          progressPercent: null,
          downloadedBytes: null,
          totalBytes: null,
          error: null,
          artifact: {
            file_name: 'video.mp4',
            content_type: 'video/mp4',
            size_bytes: 1024,
            sha256: 'abc123',
            expires_at: new Date(Date.now() + 60_000).toISOString(),
          },
          createdAt: null,
          updatedAt: null,
        },
      }),
    );
    useDownloadUrlMock.mockReturnValue(urlState({ request }));
    render(<DownloadJobPage />);
    expect(screen.getByText('视频已准备好')).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: /获取文件/ }));
    await waitFor(() => expect(request).toHaveBeenCalledTimes(1));
  });

  it('rejects expired signed URLs and handles artifacts without optional fields', async () => {
    const request = vi.fn().mockResolvedValue({
      url: 'https://minio.example.test/file.mp4',
      expiresAt: new Date(Date.now() - 60_000).toISOString(),
    });
    useDownloadJobMock.mockReturnValue(
      jobState({
        data: {
          id: 'job-1',
          status: 'succeeded',
          artifact: { file_name: 'video.mp4', content_type: 'video/mp4' },
        },
      }),
    );
    useDownloadUrlMock.mockReturnValue(urlState({ request }));
    render(<DownloadJobPage />);
    fireEvent.click(screen.getByRole('button', { name: /获取文件/ }));
    await waitFor(() => expect(request).toHaveBeenCalledTimes(1));
    expect(screen.queryByText('SHA-256')).not.toBeInTheDocument();
  });

  it('guards incomplete and unknown states and displays URL failures', () => {
    useDownloadJobMock.mockReturnValue(
      jobState({ data: { id: 'job', status: 'succeeded', artifact: null } }),
    );
    render(<DownloadJobPage />);
    expect(screen.getByText('文件信息不可用')).toBeInTheDocument();
    useDownloadJobMock.mockReturnValue(
      jobState({ data: { id: 'job', status: 'other', artifact: null } }),
    );
    useDownloadUrlMock.mockReturnValue(
      urlState({ problem: { title: '签发失败', detail: '已过期' } }),
    );
    render(<DownloadJobPage />);
    expect(screen.getByText('任务状态未知')).toBeInTheDocument();
    expect(screen.getByText('签发失败')).toBeInTheDocument();
  });

  it('shows a dedicated invalid-link result when the route has no job ID', () => {
    routeParams = {};
    render(<DownloadJobPage />);
    expect(screen.getByText('任务链接无效')).toBeInTheDocument();
  });
});
