import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import FormatPicker from '@/features/download/FormatPicker';
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
    fireEvent.click(option);

    expect(onChange).toHaveBeenCalledWith(inspection.formats[0].id);
  });
});
