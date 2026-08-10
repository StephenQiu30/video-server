import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Switch } from '@/components/ui/switch';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

describe('shared component geometry', () => {
  it('keeps switch state transitions limited to paint properties', () => {
    render(<Switch aria-label="Feature enabled" />);
    const control = screen.getByRole('switch', { name: 'Feature enabled' });
    const classes = control.className;

    expect(classes).toContain(
      'transition-[background-color,border-color,box-shadow,opacity]',
    );
    expect(classes).not.toContain('transition-all');
    fireEvent.click(control);
    expect(control).toHaveAttribute('data-state', 'checked');
    expect(control.className).toBe(classes);
  });

  it('keeps tab selection transitions limited to paint properties', () => {
    const { rerender } = render(
      <Tabs value="first">
        <TabsList>
          <TabsTrigger value="first">First</TabsTrigger>
          <TabsTrigger value="second">Second</TabsTrigger>
        </TabsList>
      </Tabs>,
    );
    const second = screen.getByRole('tab', { name: 'Second' });
    const classes = second.className;

    expect(classes).toContain(
      'transition-[background-color,border-color,box-shadow,color,opacity]',
    );
    expect(classes).not.toContain('transition-all');
    rerender(
      <Tabs value="second">
        <TabsList>
          <TabsTrigger value="first">First</TabsTrigger>
          <TabsTrigger value="second">Second</TabsTrigger>
        </TabsList>
      </Tabs>,
    );
    const activeSecond = screen.getByRole('tab', { name: 'Second' });
    expect(activeSecond).toHaveAttribute('data-state', 'active');
    expect(activeSecond.className).toBe(classes);
  });
});
