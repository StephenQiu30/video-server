import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Alert, AlertDescription } from '@/components/ui/alert';

describe('Alert', () => {
  it('keeps description text fully opaque for semantic color contrast', () => {
    render(
      <Alert variant="warning">
        <AlertDescription>需要人工核对</AlertDescription>
      </Alert>,
    );

    const description = screen.getByText('需要人工核对');
    expect(description).toHaveClass('text-sm');
    expect(description).not.toHaveClass('opacity-85');
  });
});
