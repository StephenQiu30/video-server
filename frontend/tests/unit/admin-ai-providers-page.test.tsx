import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { AiProviderScreen } from '@/components/admin/admin-ai-providers/ai-provider-screen';

describe('administrator AI Provider screen', () => {
  it('separates agent availability from the active execution route', () => {
    const onActivate = vi.fn();
    render(
      <AiProviderScreen
        agentAvailable={false}
        error=""
        items={[localCodex(), custom()]}
        loading={false}
        notice=""
        onActivate={onActivate}
        onCreate={vi.fn()}
        onDelete={vi.fn()}
        onEdit={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(
      screen.getByRole('heading', { level: 1, name: 'AI 服务' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Agent 离线')).toBeInTheDocument();
    expect(screen.getByText('本机 Agent')).toBeInTheDocument();
    expect(screen.getByText('当前用户登录')).toBeInTheDocument();
    expect(screen.getByText('gpt-5.6-sol')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '启用' }));
    expect(onActivate).toHaveBeenCalledWith(custom());
  });

  it('keeps the active Provider protected from deletion', () => {
    render(
      <AiProviderScreen
        agentAvailable
        error=""
        items={[localCodex()]}
        loading={false}
        notice=""
        onActivate={vi.fn()}
        onCreate={vi.fn()}
        onDelete={vi.fn()}
        onEdit={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText('Agent 在线')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: '删除 本机 Codex' }),
    ).toBeDisabled();
  });

  it('renders the optional DeepSeek LangChain route', () => {
    render(
      <AiProviderScreen
        agentAvailable
        error=""
        items={[deepSeek()]}
        loading={false}
        notice=""
        onActivate={vi.fn()}
        onCreate={vi.fn()}
        onDelete={vi.fn()}
        onEdit={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText('LangChain · DeepSeek')).toBeInTheDocument();
    expect(screen.getByText('https://api.deepseek.com')).toBeInTheDocument();
    expect(
      screen.getByText('deepseek-v4-flash-vision-exp'),
    ).toBeInTheDocument();
  });
});

function localCodex(): API.AiProviderProfileResponse {
  return {
    auth_mode: 'host_login',
    base_url: null,
    created_at: '2026-08-13T00:00:00Z',
    credential_configured: false,
    display_name: '本机 Codex',
    engine: 'codex',
    is_active: true,
    key: 'local-codex',
    model: 'gpt-5.6-sol',
    updated_at: '2026-08-13T00:00:00Z',
  };
}

function custom(): API.AiProviderProfileResponse {
  return {
    auth_mode: 'api_key',
    base_url: 'https://api.example.com/v1',
    created_at: '2026-08-13T00:00:00Z',
    credential_configured: true,
    display_name: '备用线路',
    engine: 'codex',
    is_active: false,
    key: 'backup',
    model: 'gpt-custom',
    updated_at: '2026-08-13T00:00:00Z',
  };
}

function deepSeek(): API.AiProviderProfileResponse {
  return {
    auth_mode: 'api_key',
    base_url: 'https://api.deepseek.com',
    created_at: '2026-08-29T00:00:00Z',
    credential_configured: true,
    display_name: 'DeepSeek 主线路',
    engine: 'deepseek',
    is_active: true,
    key: 'deepseek-main',
    model: 'deepseek-v4-flash-vision-exp',
    updated_at: '2026-08-29T00:00:00Z',
  };
}
