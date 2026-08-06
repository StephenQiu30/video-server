import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import FormatPicker from '@/components/FormatPicker';
import { inspection } from './download-fixtures';

describe('FormatPicker', () => {
  it('shows an empty state and emits the selected format', () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <FormatPicker formats={[]} onChange={onChange} selectedId="" />,
    );

    expect(screen.getByText('没有可用的下载格式。')).toBeInTheDocument();

    rerender(
      <FormatPicker
        formats={inspection.formats}
        onChange={onChange}
        selectedId=""
      />,
    );
    const option = screen.getByRole('radio', { name: /1080p MP4/ });
    expect(option).not.toBeChecked();
    expect(screen.getByText('推荐')).toBeInTheDocument();
    fireEvent.click(option);

    expect(onChange).toHaveBeenCalledWith(inspection.formats[0].id);
  });

  it('keeps the initial format list compact and expands on demand', () => {
    const formats = Array.from({ length: 8 }, (_, index) => ({
      ...inspection.formats[0],
      id: `format-${index}`,
      display_name: `${1080 - index * 90}p MP4`,
    }));

    render(
      <FormatPicker
        formats={formats}
        onChange={vi.fn()}
        selectedId={formats[0].id}
      />,
    );

    expect(screen.getAllByRole('radio')).toHaveLength(4);
    fireEvent.click(screen.getByRole('button', { name: /查看全部 8 个格式/ }));
    expect(screen.getAllByRole('radio')).toHaveLength(8);
    expect(
      screen.getByRole('button', { name: /收起格式/ }),
    ).toBeInTheDocument();
  });
});
