import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Progress } from '@/components/ui/progress';

describe('Progress', () => {
  it('exposes the visual value through Radix progress semantics', () => {
    render(<Progress aria-label="任务进度" value={35} />);

    expect(
      screen.getByRole('progressbar', { name: '任务进度' }),
    ).toHaveAttribute('aria-valuenow', '35');
  });

  it('preserves Radix indeterminate semantics when value is null', () => {
    render(<Progress aria-label="会话状态" value={null} />);

    expect(
      screen.getByRole('progressbar', { name: '会话状态' }),
    ).not.toHaveAttribute('aria-valuenow');
  });
});
