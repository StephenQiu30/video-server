import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import LegalNotice from '../../src/components/LegalNotice';

describe('LegalNotice', () => {
  it('shows the public-content use notice as text', () => {
    render(<LegalNotice />);
    expect(screen.getByText(/仅下载你有权使用的公开内容/)).toBeInTheDocument();
  });
});
