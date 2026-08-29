import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AdminAiProvidersView } from '@/components/admin/admin-ai-providers-view';

const runtime = vi.hoisted(() => ({
  activate: vi.fn(),
  create: vi.fn(),
  delete: vi.fn(),
  list: vi.fn(),
  update: vi.fn(),
}));

vi.mock('@/services/ai-providers', () => ({
  activateAiProviderProfile: runtime.activate,
  createAiProviderProfile: runtime.create,
  deleteAiProviderProfile: runtime.delete,
  displayError: (reason: unknown) =>
    reason instanceof Error ? reason.message : '请求失败',
  listAiProviderProfiles: runtime.list,
  updateAiProviderProfile: runtime.update,
}));

describe('administrator AI Provider mutations', () => {
  beforeEach(() => {
    for (const mock of Object.values(runtime)) mock.mockReset();
    runtime.list.mockResolvedValue({
      agent_available: true,
      items: [localCodex()],
    });
    runtime.update.mockResolvedValue(localCodex());
  });

  it('sends only editable fields when updating local Codex', async () => {
    render(<AdminAiProvidersView />);

    fireEvent.click(
      await screen.findByRole('button', { name: '编辑 本机 Codex' }),
    );
    const dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText('显示名称'), {
      target: { value: '本机 Codex App Server' },
    });
    fireEvent.change(within(dialog).getByLabelText('模型'), {
      target: { value: 'gpt-next' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: '保存配置' }));

    await waitFor(() =>
      expect(runtime.update).toHaveBeenCalledWith('local-codex', {
        display_name: '本机 Codex App Server',
        model: 'gpt-next',
      }),
    );
    expect(runtime.delete).not.toHaveBeenCalled();
  });
});

function localCodex(): API.AiProviderProfileResponse {
  return {
    auth_mode: 'host_login',
    base_url: null,
    created_at: '2026-08-29T00:00:00Z',
    credential_configured: false,
    display_name: '本机 Codex',
    engine: 'codex',
    is_active: false,
    key: 'local-codex',
    model: 'gpt-5.6-sol',
    updated_at: '2026-08-29T00:00:00Z',
  };
}
