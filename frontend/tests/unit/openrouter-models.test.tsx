import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { OpenRouterModels } from '@/components/admin/admin-ai-providers/openrouter-models';

const list = vi.hoisted(() => vi.fn());
vi.mock('@/services/ai-providers', () => ({
  listOpenRouterModels: list,
  displayError: () => '模型目录暂时不可用',
}));
beforeEach(() => list.mockReset());

it('loads model capabilities and lets the user select a compatible model', async () => {
  list.mockResolvedValue({
    items: [
      {
        id: 'vendor/vision',
        name: 'Vision',
        input_modalities: ['text', 'image'],
        output_modalities: ['text'],
        supported_parameters: ['structured_outputs'],
      },
      {
        id: 'vendor/plain',
        name: 'Plain',
        input_modalities: ['text'],
        output_modalities: ['text'],
        supported_parameters: [],
      },
    ],
  });
  const select = vi.fn();
  render(<OpenRouterModels disabled={false} onSelect={select} />);
  expect(list).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: '读取 OpenRouter 模型' }));
  await screen.findByText(/1 个匹配模型/);
  fireEvent.click(screen.getByRole('combobox', { name: '目录中的模型' }));
  const menu = await screen.findByRole('listbox');
  fireEvent.click(
    within(menu).getByRole('option', { name: 'vendor/vision · 支持图像' }),
  );
  expect(select).toHaveBeenCalledWith('vendor/vision');
});

it('shows an unavailable catalog and supports retry', async () => {
  list
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce({ items: [] });
  render(<OpenRouterModels disabled={false} onSelect={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: '读取 OpenRouter 模型' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(
    '模型目录暂时不可用',
  );
  fireEvent.click(screen.getByRole('button', { name: '读取 OpenRouter 模型' }));
  await screen.findByText(/0 个匹配模型/);
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
