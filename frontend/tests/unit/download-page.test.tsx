import { fireEvent, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DownloadWorkspace from '@/components/intake/download-workspace';
import { PUBLIC_INPUT_REQUIRED } from '@/components/intake/public-input';
import { TooltipProvider } from '@/components/ui/tooltip';
import { httpClient } from '@/lib/request';
import { ApiError } from '@/lib/request-error';
import {
  galleryInspection,
  galleryJob,
  inspection,
  job,
  reportedDouyinShareMessage,
  sourceDiscovery,
  videoCollectionInspection,
} from '../fixtures/download-fixtures';
import { intentFixture } from '../fixtures/intent-fixtures';
import {
  httpRequests,
  mockHttpError,
  mockHttpResponses,
} from '../helpers/http';
import { render } from '../helpers/query-render';

const push = vi.fn();
const authorization = vi.hoisted(() => ({
  begin: vi.fn(),
  cancel: vi.fn(),
  get: vi.fn(),
}));
const auth = vi.hoisted(() => ({
  user: { id: 'intent-test-owner', role: 'admin' },
}));

vi.mock('@/api/providers', () => ({
  beginProviderAuthorization: authorization.begin,
  cancelProviderAuthorization: authorization.cancel,
  getProviderAuthorization: authorization.get,
}));

vi.mock('@/components/providers/use-provider-statuses', () => ({
  useProviderStatuses: () => ({
    data: { items: [] },
    error: null,
    loading: false,
    retry: vi.fn(),
  }),
}));

vi.mock('@/components/auth/auth-provider', () => ({
  useAuth: () => ({ user: auth.user }),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}));

describe('DownloadWorkspace', () => {
  beforeEach(() => {
    auth.user = { id: 'intent-test-owner', role: 'admin' };
    push.mockReset();
    authorization.begin.mockReset();
    authorization.cancel.mockReset();
    authorization.cancel.mockResolvedValue(undefined);
    authorization.get.mockReset();
    window.history.replaceState({}, '', '/');
  });

  it('does not turn provider verification failures into account authorization', async () => {
    auth.user = { id: 'intent-test-owner', role: 'user' };
    mockHttpResponses(
      intentFixture({
        status: 'failed',
        inspection_id: null,
        reason_code: 'provider_verification_failed',
      }),
    );
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'https://www.youtube.com/watch?v=regular-user' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(
      await screen.findByText(
        '平台要求额外验证，当前公开路线暂不可用，请稍后重试或更换公开链接。',
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '使用托管线路重试' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '使用隔离浏览器会话' }),
    ).not.toBeInTheDocument();
    expect(authorization.begin).not.toHaveBeenCalled();
  });

  it('renders the inspection form and source tabs', () => {
    renderWorkspace();

    const input = screen.getByLabelText('公开视频地址');
    expect(input).toHaveClass('field-sizing-fixed');
    expect(screen.getByRole('button', { name: '解析媒体' })).toBeEnabled();
    expect(screen.getByRole('tab', { name: '链接解析' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    expect(screen.getByRole('tab', { name: '本地视频' })).toBeEnabled();
    expect(screen.getByRole('tab', { name: '剧本文档' })).toBeEnabled();
    expect(
      document.querySelector('[data-slot="inspection-result"]'),
    ).not.toBeInTheDocument();
  });

  it('offers screenplay import from the same home intake', async () => {
    renderWorkspace();

    fireEvent.mouseDown(screen.getByRole('tab', { name: '剧本文档' }), {
      button: 0,
      ctrlKey: false,
    });
    const fileInput = screen.getByLabelText('选择剧本文档文件');
    expect(fileInput).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '上传剧本' }));
    expect(
      await screen.findByText('请先选择一份剧本文档。'),
    ).toBeInTheDocument();
  });

  it('rejects blank input before making an API request', async () => {
    renderWorkspace();

    const input = screen.getByLabelText('公开视频地址');
    fireEvent.change(input, { target: { value: '' } });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    const error = await screen.findByText(PUBLIC_INPUT_REQUIRED);
    expect(error).toHaveAttribute('id', 'download-workspace-error');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAttribute(
      'aria-describedby',
      'download-workspace-error',
    );
    expect(httpRequests()).toHaveLength(0);
  });

  it('clears a stale inspection when the URL changes', async () => {
    mockReadyInspection(inspection);
    renderWorkspace();

    const input = screen.getByLabelText('公开视频地址');
    fireEvent.change(input, {
      target: { value: 'https://media.example/owned' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));
    expect(await screen.findByText(inspection.title)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: '创建下载任务' }),
    ).toBeInTheDocument();

    fireEvent.change(input, { target: { value: '' } });

    expect(screen.queryByText(inspection.title)).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '创建下载任务' }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));
    expect(await screen.findByText(PUBLIC_INPUT_REQUIRED)).toBeInTheDocument();
  });

  it('locks the submitted URL until its inspection response is applied', async () => {
    let resolveInspection:
      | ((value: { data: API.IntentResponse }) => void)
      | undefined;
    vi.mocked(httpClient.request).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveInspection = resolve;
        }) as never,
    );
    renderWorkspace();

    const input = screen.getByLabelText('公开视频地址');
    fireEvent.change(input, {
      target: { value: 'https://media.example/submitted' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(
      await screen.findByRole('button', { name: '解析中…' }),
    ).toBeDisabled();
    expect(input).toBeDisabled();
    expect(screen.getByRole('button', { name: '清空链接' })).toBeDisabled();

    mockHttpResponses(inspection);
    resolveInspection?.({ data: intentFixture() });
    expect(await screen.findByText(inspection.title)).toBeInTheDocument();
    expect(input).toBeEnabled();
  });

  it('sends the original share message to the server for inspection', async () => {
    mockReadyInspection(inspection);
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: reportedDouyinShareMessage },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(await screen.findByText(inspection.title)).toBeInTheDocument();
    expect(httpRequests()[0]).toMatchObject({
      data: {
        input: reportedDouyinShareMessage,
      },
      method: 'POST',
      url: '/api/download-intents',
    });
  });

  it('sends the complete Hongguo share message without client rewriting', async () => {
    mockReadyInspection(inspection);
    renderWorkspace();

    const shareMessage =
      '漫剧《死对头校花竟是我网恋女友》 - 免费好剧，尽在红果\n' +
      '点击链接打开👉https://novelquickapp.com/s/QVcr7YNEMwI/\n' +
      '复制本条消息后，打开「红果短剧App」后免费看全集~';
    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: shareMessage },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(await screen.findByText(inspection.title)).toBeInTheDocument();
    expect(httpRequests()[0]).toMatchObject({
      data: {
        input: shareMessage,
      },
    });
  });

  it('does not mark the URL field invalid when inspection fails downstream', async () => {
    mockHttpResponses(
      intentFixture({
        status: 'failed',
        inspection_id: null,
        reason_code: 'inspection_timeout',
      }),
    );
    renderWorkspace();

    const input = screen.getByLabelText('公开视频地址');
    fireEvent.change(input, {
      target: { value: 'https://media.example/slow' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(
      await screen.findByText('读取视频信息超时，请稍后重试。'),
    ).toBeInTheDocument();
    expect(input).not.toHaveAttribute('aria-invalid');
    expect(input).not.toHaveAttribute('aria-describedby');
  });

  it('does not retry ambiguous verification failures with an account session', async () => {
    mockHttpResponses(
      intentFixture({
        status: 'failed',
        inspection_id: null,
        reason_code: 'provider_verification_failed',
      }),
    );
    renderWorkspace();

    const url = 'https://www.youtube.com/watch?v=owned';
    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: url },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(
      await screen.findByText(
        '平台要求额外验证，当前公开路线暂不可用，请稍后重试或更换公开链接。',
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '使用托管线路重试' }),
    ).not.toBeInTheDocument();
    expect(httpRequests()).toHaveLength(1);
    expect(authorization.begin).not.toHaveBeenCalled();
  });

  it('offers the managed Yuanbao session for WeChat Channels', async () => {
    const url = 'https://weixin.qq.com/sph/AvvqOTT0yG';
    mockHttpResponses(
      intentFixture({
        status: 'failed',
        inspection_id: null,
        reason_code: 'provider_auth_required',
      }),
    );
    mockHttpResponses(inspection);
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: url },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(
      await screen.findByText(
        '该链接明确需要平台账号权限，请使用部署方提供的受控授权路线或更换公开链接。',
      ),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '使用托管线路重试' }));

    expect(await screen.findByText(inspection.title)).toBeInTheDocument();
    expect(httpRequests()[1]).toMatchObject({
      data: {
        source: {
          access_policy_id: 'operator_public',
          kind: 'public_url',
          url,
        },
      },
    });
    expect(authorization.begin).not.toHaveBeenCalled();
  });

  it('does not mark the URL field invalid when task creation fails', async () => {
    mockReadyInspection(inspection);
    mockHttpError(
      new ApiError(503, 'download_failed', '创建失败', '任务创建失败。'),
    );
    renderWorkspace();

    const input = screen.getByLabelText('公开视频地址');
    fireEvent.change(input, {
      target: { value: 'https://media.example/owned' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));
    await screen.findByText(inspection.title);
    fireEvent.click(screen.getByRole('button', { name: '创建下载任务' }));

    expect(await screen.findByText('任务创建失败。')).toBeInTheDocument();
    expect(input).not.toHaveAttribute('aria-invalid');
    expect(input).not.toHaveAttribute('aria-describedby');
  });

  it('keeps the media result in place when a parsed URL becomes a download', async () => {
    mockReadyInspection(inspection, job(), job());
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: ' https://media.example/owned ' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(await screen.findByText(inspection.title)).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '画质预设' }),
    ).toBeInTheDocument();
    expect(screen.getByText('体积优先')).toBeInTheDocument();
    expect(screen.getByRole('radio')).toBeChecked();
    const parsedResult = document.querySelector('[data-slot="media-result"]');
    expect(
      parsedResult?.querySelector('[data-slot="media-result-frame"]'),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '创建下载任务' }));

    expect(
      await screen.findByRole('heading', { name: '下载即将开始' }),
    ).toBeInTheDocument();
    const downloadResult = document.querySelector('[data-slot="media-result"]');
    expect(downloadResult?.className).toBe(parsedResult?.className);
    expect(
      downloadResult?.querySelector('[data-slot="media-result-frame"]'),
    ).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '画质预设' })).toBeNull();
    expect(push).not.toHaveBeenCalled();
    expect(httpRequests()).toMatchObject([
      {
        data: {
          input: 'https://media.example/owned',
        },
        headers: { 'Idempotency-Key': expect.any(String) },
        method: 'POST',
        url: '/api/download-intents',
      },
      { method: 'GET', url: `/api/inspections/${inspection.id}` },
      {
        data: {
          format_id: inspection.formats[0].id,
          inspection_id: inspection.id,
        },
        headers: { 'Idempotency-Key': expect.any(String) },
        method: 'POST',
        url: '/api/downloads',
      },
    ]);
  });

  it('shows an official image note as a ZIP download option', async () => {
    mockReadyInspection(galleryInspection, galleryJob());
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'https://v.douyin.com/qao3WztsXns/' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(await screen.findByText('官方图文作品')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '下载内容' }),
    ).toBeInTheDocument();
    expect(screen.getByText('下载 3 张原图（ZIP）')).toBeInTheDocument();
    expect(screen.getByText('图文作品 · 3 张原图')).toBeInTheDocument();
    expect(screen.getByText('原图打包')).toBeInTheDocument();
  });

  it('shows a multi-video source as a ZIP download option', async () => {
    mockReadyInspection(videoCollectionInspection);
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'https://www.instagram.com/p/example/' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(
      await screen.findByRole('heading', { name: '视频合集' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: '下载内容' }),
    ).toBeInTheDocument();
    expect(screen.getByText('下载 2 个视频（ZIP）')).toBeInTheDocument();
    expect(screen.getByText('视频合集 · 2 个视频')).toBeInTheDocument();
    expect(screen.getByText('视频合集 · 视频 ZIP')).toBeInTheDocument();
  });

  it('routes a recognized WeChat Channels source to owned-file upload', async () => {
    mockReadyInspection({
      ...inspection,
      extractor_key: 'wechat_channels',
      title: '微信视频号内容',
      duration_seconds: 0,
      formats: [],
      execution_mode: 'verified_import',
      access_decision: 'export_required',
      entitlement_state: 'unknown',
      protection_state: 'unknown',
      rights_basis: null,
      restriction_reason: 'wechat_channels_export_required',
      user_action: '请在微信中合法导出自有明文 MP4 后通过本地导入上传。',
    });
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'https://weixin.qq.com/sph/AbCdEf12' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(await screen.findByText('需要导入自有文件')).toBeInTheDocument();
    expect(
      screen.getByText('请在微信中合法导出自有明文 MP4 后通过本地导入上传。'),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('wechat_channels_export_required'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '创建下载任务' }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(
      '媒体解析完成，结果已显示。',
    );

    fireEvent.click(screen.getByRole('button', { name: '上传自有 MP4' }));
    const videoTab = screen.getByRole('tab', { name: '本地视频' });
    expect(videoTab).toHaveAttribute('aria-selected', 'true');
    expect(videoTab).toHaveFocus();
    expect(screen.getByRole('status')).toBeEmptyDOMElement();
  });

  it('discovers article embeds and requires an explicit item selection', async () => {
    mockHttpResponses(sourceDiscovery, {
      ...inspection,
      extractor_key: 'wechat_channels',
      title: '视频号片段',
      duration_seconds: 0,
      formats: [],
      execution_mode: 'verified_import',
      access_decision: 'export_required',
      entitlement_state: 'unknown',
      protection_state: 'unknown',
      rights_basis: null,
      restriction_reason: 'wechat_channels_export_required',
      user_action: '请在微信中合法导出自有明文 MP4 后通过本地导入上传。',
    });
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'https://mp.weixin.qq.com/s/article_123' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(
      await screen.findByRole('heading', { name: sourceDiscovery.title }),
    ).toBeInTheDocument();
    expect(screen.getByText('不会自动选择第一项')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '选择并查看' })).toHaveLength(
      2,
    );
    expect(httpRequests()).toHaveLength(1);
    expect(httpRequests()[0]).toMatchObject({
      data: {
        kind: 'wechat_official_account_article',
        url: 'https://mp.weixin.qq.com/s/article_123',
      },
      method: 'POST',
      url: '/api/source-discoveries',
    });

    fireEvent.click(screen.getAllByRole('button', { name: '选择并查看' })[0]);

    expect(await screen.findByText('需要导入自有文件')).toBeInTheDocument();
    expect(httpRequests()[1]).toMatchObject({
      data: {
        source: {
          kind: 'discovered_item',
          discovery_id: sourceDiscovery.id,
          item_ref: sourceDiscovery.items[0].item_ref,
        },
      },
      method: 'POST',
      url: '/api/inspections',
    });
  });

  it('does not offer a download for Tencent consumer playback content', async () => {
    mockReadyInspection({
      ...inspection,
      extractor_key: 'qqvideo',
      title: '腾讯视频内容',
      duration_seconds: 0,
      formats: [],
      access_decision: 'playback_only',
      entitlement_state: 'unknown',
      protection_state: 'unknown',
      rights_basis: null,
      restriction_reason: 'tencent_consumer_download_disabled',
      user_action: '请在腾讯视频官方客户端播放；VIP/付费内容不提供下载。',
    });
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'https://v.qq.com/x/page/q326831cny0.html' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(await screen.findByText('仅支持官方播放')).toBeInTheDocument();
    expect(
      screen.getByText('请在腾讯视频官方客户端播放；VIP/付费内容不提供下载。'),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('tencent_consumer_download_disabled'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '创建下载任务' }),
    ).not.toBeInTheDocument();
  });

  it('labels a blocked inspection as currently unavailable', async () => {
    mockReadyInspection({
      ...inspection,
      formats: [],
      access_decision: 'blocked',
      restriction_reason: 'article_native_download_not_enabled',
      user_action: '安全下载执行器完成授权验收前暂不提供下载。',
    });
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'https://media.example/blocked-video' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(await screen.findByText('当前不可下载')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '创建下载任务' }),
    ).not.toBeInTheDocument();
  });
});

function renderWorkspace() {
  return render(
    <TooltipProvider>
      <DownloadWorkspace />
    </TooltipProvider>,
  );
}

function mockReadyInspection(
  value: API.InspectionResponse,
  ...more: unknown[]
) {
  mockHttpResponses(intentFixture({ inspection_id: value.id }), value, ...more);
}
