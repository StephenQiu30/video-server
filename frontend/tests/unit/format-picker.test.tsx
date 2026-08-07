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
    expect(screen.queryByText('推荐')).not.toBeInTheDocument();
    fireEvent.click(option);

    expect(onChange).toHaveBeenCalledWith(inspection.formats[0].id);
  });

  it('keeps the initial format list compact and paginates on demand', () => {
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
    fireEvent.click(screen.getByTitle('2'));
    expect(screen.getAllByRole('radio')).toHaveLength(4);
    expect(screen.getByText('450p MP4')).toBeInTheDocument();
  });
});
