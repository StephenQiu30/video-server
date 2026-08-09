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
});
