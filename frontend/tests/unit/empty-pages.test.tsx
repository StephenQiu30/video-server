import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import NotFound from '@/app/not-found';
import MissingDownload from '@/components/downloads/missing-download';

describe('empty route states', () => {
  it('gives the not-found page a semantic page title', () => {
    render(<NotFound />);

    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
  });

  it('gives a missing download a semantic page title', () => {
    const { container } = render(<MissingDownload />);

    const heading = screen.getByRole('heading', { level: 1 });
    const backLink = screen.getByRole('link', { name: '返回上一步' });

    expect(heading).toBeInTheDocument();
    expect(backLink).toHaveAttribute('href', '/history');
    expect(
      container.querySelector('[data-slot="empty-icon"]'),
    ).toBeInTheDocument();
    expect(backLink.compareDocumentPosition(heading)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
  });
});
