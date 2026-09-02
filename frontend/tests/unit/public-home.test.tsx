import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PublicHome } from '@/components/intake/public-home';

describe('PublicHome', () => {
  it('reuses the editorial hierarchy on a continuous borderless canvas', () => {
    const { container } = render(<PublicHome />);

    expect(
      screen.getByRole('heading', {
        level: 1,
        name: /把素材，\s*带回本地。/,
      }),
    ).toHaveClass('editorial-title');
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(3);
    expect(
      container.querySelectorAll('[data-slot="editorial-intro"]'),
    ).toHaveLength(4);
    expect(container.querySelectorAll('[data-slot="item-group"]')).toHaveLength(
      3,
    );
    expect(
      container.querySelector('[data-home-reveal]'),
    ).not.toBeInTheDocument();

    const sections = container.querySelectorAll(
      '[data-slot="borderless-section"]',
    );
    expect(sections).toHaveLength(4);
    for (const section of sections) {
      expect(section.className).not.toMatch(/\bborder(?:-|\b)/);
    }
  });

  it('keeps the public conversion and documentation paths available', () => {
    render(<PublicHome />);

    expect(screen.getByRole('link', { name: /创建本地账户/ })).toHaveAttribute(
      'href',
      '/user/register',
    );
    expect(screen.getByRole('link', { name: /查看源代码/ })).toHaveAttribute(
      'href',
      'https://github.com/StephenQiu30/video-server',
    );
    expect(screen.getByRole('link', { name: /阅读部署说明/ })).toHaveAttribute(
      'href',
      'https://github.com/StephenQiu30/video-server/blob/main/README.md#快速开始',
    );
  });
});
