import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { AiProviderEditor } from '@/components/admin/admin-ai-providers/ai-provider-editor';
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

  it('keeps local Codex protected from deletion even while inactive', () => {
    render(
      <AiProviderScreen
        agentAvailable
        error=""
        items={[localCodex({ is_active: false })]}
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
    expect(screen.getByText('系统兜底')).toBeInTheDocument();
  });

  it('only enables non-structural fields for the local Codex fallback', () => {
    render(
      <AiProviderEditor
        editor={{
          apiKey: '',
          authMode: 'host_login',
          baseUrl: '',
          credentialConfigured: false,
          displayName: '本机 Codex',
          engine: 'codex',
          error: '',
          key: 'local-codex',
          mode: 'edit',
          model: 'gpt-5.6-sol',
          saving: false,
        }}
        onChange={vi.fn()}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    );

    expect(screen.getByLabelText('配置标识')).toBeDisabled();
    expect(screen.getByLabelText('显示名称')).toBeEnabled();
    expect(screen.getByLabelText('模型')).toBeEnabled();
    expect(screen.getByRole('combobox', { name: '执行引擎' })).toBeDisabled();
    expect(screen.getByRole('combobox', { name: '认证方式' })).toBeDisabled();
    expect(screen.getByText(/只能修改显示名称和模型/)).toBeInTheDocument();
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

  it.each(['create', 'edit'] as const)(
    'locks the fixed DeepSeek vision model while in %s mode',
    (mode) => {
      render(
        <AiProviderEditor
          editor={{
            apiKey: '',
            authMode: 'api_key',
            baseUrl: 'https://api.deepseek.com',
            credentialConfigured: mode === 'edit',
            displayName: 'DeepSeek 主线路',
            engine: 'deepseek',
            error: '',
            key: 'deepseek-main',
            mode,
            model: 'deepseek-v4-flash-vision-exp',
            saving: false,
          }}
          onChange={vi.fn()}
          onClose={vi.fn()}
          onSave={vi.fn()}
        />,
      );

      expect(screen.getByLabelText('模型')).toBeDisabled();
      expect(screen.getByLabelText('模型')).toHaveValue(
        'deepseek-v4-flash-vision-exp',
      );
      expect(
        screen.getByText('当前 LangChain 视觉适配器固定使用此模型。'),
      ).toBeInTheDocument();
    },
  );
});

function localCodex(
  values: Partial<API.AiProviderProfileResponse> = {},
): API.AiProviderProfileResponse {
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
    ...values,
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
