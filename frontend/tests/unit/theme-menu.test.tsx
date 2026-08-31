import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ThemeMenu } from '@/components/layout/theme-menu';

const themeRuntime = vi.hoisted(() => ({
  setTheme: vi.fn(),
  theme: 'system',
}));

vi.mock('next-themes', () => ({
  useTheme: () => themeRuntime,
}));

describe('ThemeMenu', () => {
  beforeEach(() => {
    themeRuntime.setTheme.mockReset();
    themeRuntime.theme = 'system';
  });

  it('offers light, dark, and system themes through an accessible menu', async () => {
    render(<ThemeMenu />);

    const trigger = await screen.findByRole('button', {
      name: '切换主题，当前：跟随系统',
    });
    expect(trigger).toHaveClass('size-11');

    fireEvent.pointerDown(trigger, { button: 0, ctrlKey: false });

    const systemOption = await screen.findByRole('menuitemradio', {
      name: '跟随系统',
    });
    expect(systemOption).toHaveAttribute('aria-checked', 'true');
    expect(
      screen.getByRole('menuitemradio', { name: '浅色' }),
    ).toBeInTheDocument();
    const darkOption = screen.getByRole('menuitemradio', { name: '深色' });

    fireEvent.click(darkOption);
    await waitFor(() =>
      expect(themeRuntime.setTheme).toHaveBeenCalledWith('dark'),
    );
  });
});
