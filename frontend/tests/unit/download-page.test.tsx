import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import DownloadWorkspace from '@/components/intake/download-workspace';
import { TooltipProvider } from '@/components/ui/tooltip';
import { httpClient } from '@/lib/request';
import { ApiError } from '@/services/download';
import { URL_MESSAGE } from '@/utils/validation';
import {
  inspection,
  galleryInspection,
  galleryJob,
  job,
  reportedDouyinShareMessage,
  sourceDiscovery,
} from '../fixtures/download-fixtures';
import {
  httpRequests,
  mockHttpError,
  mockHttpResponses,
} from '../helpers/http';

vi.mock('next/navigation', () => ({}));

describe('DownloadWorkspace', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/');
  });

  it('starts with one focused, accessible inspection form', () => {
    renderWorkspace();

    expect(
      screen.getByRole('heading', { name: /把素材，\s*带回本地。/u }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/^\d{2} \/ /u)).not.toBeInTheDocument();
    expect(screen.queryByText('Public media workflow')).not.toBeInTheDocument();
    expect(screen.queryByText('02 / 选择画质')).not.toBeInTheDocument();
    expect(screen.queryByText('03 / 创建任务')).not.toBeInTheDocument();
    expect(screen.getByLabelText('公开视频地址')).toBeInTheDocument();
    expect(screen.queryByText('⌘V')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '解析媒体' })).toBeEnabled();
    expect(screen.getByRole('tab', { name: '链接解析' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    expect(screen.getByRole('tab', { name: '本地视频' })).toBeEnabled();
    expect(screen.getByRole('tab', { name: '剧本文档' })).toBeEnabled();
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(screen.queryByText(/请仅提交你有权处理/u)).not.toBeInTheDocument();
    expect(
      screen.queryByRole('region', { name: '解析结果' }),
    ).not.toBeInTheDocument();
  });

  it('offers screenplay import from the same home intake', async () => {
    renderWorkspace();

    fireEvent.mouseDown(screen.getByRole('tab', { name: '剧本文档' }), {
      button: 0,
      ctrlKey: false,
    });
    const fileInput = screen.getByLabelText('选择剧本文档文件');
    expect(fileInput).toHaveClass('sr-only');
    expect(fileInput).not.toHaveClass('w-full');
    fireEvent.click(screen.getByRole('button', { name: '上传剧本' }));
    expect(
      await screen.findByText('请先选择一份剧本文档。'),
    ).toBeInTheDocument();
  });

  it('rejects an invalid address before making an API request', async () => {
    renderWorkspace();

    const input = screen.getByLabelText('公开视频地址');
    fireEvent.change(input, {
      target: { value: 'file:///tmp/private-video' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    const error = await screen.findByText(URL_MESSAGE);
    expect(error).toHaveAttribute('id', 'download-workspace-error');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAttribute(
      'aria-describedby',
      'download-workspace-error',
    );
    expect(httpRequests()).toHaveLength(0);
  });

  it('clears a stale inspection when the URL changes', async () => {
    mockHttpResponses(inspection);
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

    fireEvent.change(input, { target: { value: 'not-a-url' } });

    expect(screen.queryByText(inspection.title)).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '创建下载任务' }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));
    expect(await screen.findByText(URL_MESSAGE)).toBeInTheDocument();
  });

  it('locks the submitted URL until its inspection response is applied', async () => {
    let resolveInspection:
      | ((value: { data: typeof inspection }) => void)
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

    resolveInspection?.({ data: inspection });
    expect(await screen.findByText(inspection.title)).toBeInTheDocument();
    expect(input).toBeEnabled();
  });

  it('normalizes the reported Douyin share message before inspection', async () => {
    mockHttpResponses(inspection);
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: reportedDouyinShareMessage },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(await screen.findByText(inspection.title)).toBeInTheDocument();
    expect(httpRequests()[0]).toMatchObject({
      data: {
        source: {
          kind: 'public_url',
          url: 'https://v.douyin.com/Tq0eYJRMYRk/',
        },
      },
      method: 'POST',
      url: '/api/inspections',
    });
  });

  it('does not mark the URL field invalid when inspection fails downstream', async () => {
    mockHttpError(
      new ApiError(504, 'inspection_timeout', '解析超时', '媒体解析超时。'),
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

  it('does not mark the URL field invalid when task creation fails', async () => {
    mockHttpResponses(inspection);
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

  it('inspects a public URL, creates a download, and opens its Next route', async () => {
    mockHttpResponses(inspection, job());
    const assign = vi
      .spyOn(window.location, 'assign')
      .mockImplementation(() => undefined);
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
    fireEvent.click(screen.getByRole('button', { name: '创建下载任务' }));

    await waitFor(() =>
      expect(assign).toHaveBeenCalledWith(
        `/downloads/detail?jobId=${encodeURIComponent(job().id)}`,
      ),
    );
    expect(httpRequests()).toMatchObject([
      {
        data: {
          source: {
            kind: 'public_url',
            url: 'https://media.example/owned',
          },
        },
        headers: { 'Idempotency-Key': expect.any(String) },
        method: 'POST',
        url: '/api/inspections',
      },
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
    mockHttpResponses(galleryInspection, galleryJob());
    renderWorkspace();

    fireEvent.change(screen.getByLabelText('公开视频地址'), {
      target: { value: 'https://v.douyin.com/qao3WztsXns/' },
    });
    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));

    expect(await screen.findByText('官方图文作品')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '下载内容' })).toBeInTheDocument();
    expect(screen.getByText('下载 3 张原图（ZIP）')).toBeInTheDocument();
    expect(screen.getByText('图文作品 · 3 张原图')).toBeInTheDocument();
    expect(screen.getByText('原图打包')).toBeInTheDocument();
  });

  it('routes a recognized WeChat Channels source to owned-file upload', async () => {
    mockHttpResponses({
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
    mockHttpResponses({
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
    mockHttpResponses({
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
