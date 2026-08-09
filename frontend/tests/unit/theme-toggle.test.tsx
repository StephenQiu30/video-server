import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ThemeToggle } from '@/components/theme-toggle';

const theme = vi.hoisted(() => ({
  resolvedTheme: 'light',
  setTheme: vi.fn(),
}));

vi.mock('next-themes', () => ({
  useTheme: () => theme,
}));

describe('ThemeToggle', () => {
  beforeEach(() => {
    theme.resolvedTheme = 'light';
    theme.setTheme.mockReset();
  });

  it('switches the shared theme from light to dark', () => {
    render(<ThemeToggle />);

    fireEvent.click(screen.getByRole('button', { name: '切换颜色主题' }));

    expect(theme.setTheme).toHaveBeenCalledWith('dark');
  });

  it('switches the shared theme from dark to light', () => {
    theme.resolvedTheme = 'dark';
    render(<ThemeToggle />);

    fireEvent.click(screen.getByRole('button', { name: '切换颜色主题' }));

    expect(theme.setTheme).toHaveBeenCalledWith('light');
  });
});
