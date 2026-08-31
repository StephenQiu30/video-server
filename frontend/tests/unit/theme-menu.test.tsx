import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ThemeMenu } from '@/components/layout/theme-menu';

const themeRuntime = vi.hoisted(() => ({
  setTheme: vi.fn(),
  theme: 'light',
}));

vi.mock('next-themes', () => ({
  useTheme: () => themeRuntime,
}));

describe('ThemeMenu', () => {
  beforeEach(() => {
    themeRuntime.setTheme.mockReset();
    themeRuntime.theme = 'light';
  });

  it('switches from light to dark with one click', async () => {
    render(<ThemeMenu />);

    const trigger = await screen.findByRole('button', {
      name: '切换到深色主题',
    });
    expect(trigger).toHaveClass('size-11');

    fireEvent.click(trigger);
    expect(themeRuntime.setTheme).toHaveBeenCalledWith('dark');
  });
});
