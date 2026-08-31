import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ThemeToggle } from '@/components/layout/theme-toggle';

const themeRuntime = vi.hoisted(() => ({
  setTheme: vi.fn(),
  theme: 'light',
}));

vi.mock('next-themes', () => ({
  useTheme: () => themeRuntime,
}));

describe('ThemeToggle', () => {
  beforeEach(() => {
    themeRuntime.setTheme.mockReset();
    themeRuntime.theme = 'light';
  });

  it('switches from light to dark with one click', async () => {
    render(<ThemeToggle />);

    const trigger = await screen.findByRole('button', {
      name: '切换到深色主题',
    });
    expect(trigger).toHaveClass('size-11');

    fireEvent.click(trigger);
    expect(themeRuntime.setTheme).toHaveBeenCalledWith('dark');
    expect(screen.queryAllByRole('menuitemradio')).toHaveLength(0);
  });

  it('switches from dark to light with one click', async () => {
    themeRuntime.theme = 'dark';
    render(<ThemeToggle />);

    const trigger = await screen.findByRole('button', {
      name: '切换到浅色主题',
    });
    fireEvent.click(trigger);
    expect(themeRuntime.setTheme).toHaveBeenCalledWith('light');
  });
});
