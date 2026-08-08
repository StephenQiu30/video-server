import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import FormatPicker from '@/components/format-picker';
import { inspection } from './download-fixtures';

describe('FormatPicker', () => {
  it('shows an empty state and emits the selected format', () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <FormatPicker formats={[]} onChange={onChange} selectedId="" />,
    );

    expect(
      screen.getByText('当前视频没有可用的下载版本。'),
    ).toBeInTheDocument();

    rerender(
      <FormatPicker
        formats={inspection.formats}
        onChange={onChange}
        selectedId=""
      />,
    );
    const option = screen.getByRole('radio', { name: /1080P · MP4/ });
    expect(option).not.toBeChecked();
    expect(screen.queryByText('推荐')).not.toBeInTheDocument();
    fireEvent.click(option);

    expect(onChange).toHaveBeenCalledWith(inspection.formats[0].id);
  });

  it('renders every semantic format as an accessible radio option', () => {
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

    expect(screen.getAllByRole('radio')).toHaveLength(8);
    expect(screen.getAllByText(/1080P · MP4/)).toHaveLength(8);
  });
});
