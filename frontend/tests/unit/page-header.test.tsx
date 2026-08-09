import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PageHeader } from '@/components/page-header';

describe('PageHeader', () => {
  it('keeps the page title, description, and optional action semantic', () => {
    render(
      <PageHeader
        action={<button type="button">新建任务</button>}
        description="查看当前任务。"
        title="任务列表"
        titleId="task-title"
      />,
    );

    expect(screen.getByRole('heading', { level: 1 })).toHaveAttribute(
      'id',
      'task-title',
    );
    expect(screen.getByRole('heading', { level: 1 })).toHaveClass(
      'text-[28px]',
      'sm:text-[32px]',
      'leading-[1.2]',
    );
    expect(screen.getByRole('banner')).not.toHaveClass('text-primary');
    expect(screen.getByText('查看当前任务。')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: '新建任务' }),
    ).toBeInTheDocument();
  });
});
