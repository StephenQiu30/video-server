import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import FormatPicker from '@/components/intake/format-picker';
import { inspection } from '../fixtures/download-fixtures';

describe('FormatPicker', () => {
  it('shows an empty state and emits the selected format', () => {
    const onChange = vi.fn();
    render(<FormatPicker formats={[]} onChange={onChange} selectedId="" />);

    expect(
      screen.getByText('当前视频没有可用的下载版本。'),
    ).toBeInTheDocument();
  });

  it('renders every semantic format as a selectable card', () => {
    const formats = Array.from({ length: 8 }, (_, index) => ({
      ...inspection.formats[0],
      id: `format-${index}`,
      display_name: `${1080 - index * 90}p MP4`,
    }));
    const onChange = vi.fn();

    render(
      <FormatPicker
        formats={formats}
        onChange={onChange}
        selectedId={formats[0].id}
      />,
    );

    expect(screen.getAllByRole('radio')).toHaveLength(8);
    expect(screen.getAllByText(/1080P/)).toHaveLength(8);

    fireEvent.click(screen.getAllByRole('radio')[1]);
    expect(onChange).toHaveBeenCalledWith('format-1');
  });
});
