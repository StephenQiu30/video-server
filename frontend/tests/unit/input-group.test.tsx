import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  InputGroup,
  InputGroupInput,
  InputGroupTextarea,
} from '@/components/ui/input-group';

describe('InputGroup controls', () => {
  it('lets the parent group own focus feedback without a child offset', () => {
    render(
      <>
        <InputGroup>
          <InputGroupInput aria-label="组合输入框" />
        </InputGroup>
        <InputGroup>
          <InputGroupTextarea aria-label="组合文本域" />
        </InputGroup>
      </>,
    );

    for (const control of [
      screen.getByRole('textbox', { name: '组合输入框' }),
      screen.getByRole('textbox', { name: '组合文本域' }),
    ]) {
      expect(control).toHaveClass('focus-visible:ring-offset-0');
      expect(control).not.toHaveClass('focus-visible:ring-offset-2');
    }
  });

  it('supports a fixed textarea row without inheriting content sizing', () => {
    render(
      <InputGroup className="h-16" textareaLayout="fixed">
        <InputGroupTextarea aria-label="固定文本域" sizing="fixed" />
      </InputGroup>,
    );

    const control = screen.getByRole('textbox', { name: '固定文本域' });
    expect(control).toHaveClass('field-sizing-fixed');
    expect(control.parentElement).toHaveAttribute(
      'data-textarea-layout',
      'fixed',
    );
    expect(control.parentElement).toHaveClass('h-16');
    expect(control.parentElement).not.toHaveClass('has-[>textarea]:h-auto');
  });
});
