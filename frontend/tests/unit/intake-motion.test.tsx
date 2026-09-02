import { act, render, screen } from '@testing-library/react';
import gsap from 'gsap';
import { describe, expect, it, vi } from 'vitest';

import {
  ContentIntakeHero,
  type IntakeMode,
} from '@/components/intake/content-intake-hero';
import { MotionReveal } from '@/components/intake/motion-reveal';

describe('intake motion', () => {
  it('keeps the initial intake still and animates only a later mode change', () => {
    mockMotionPreference(false);
    const tween = { kill: vi.fn() };
    const animate = vi.spyOn(gsap, 'fromTo').mockReturnValue(tween as never);
    const { rerender } = renderHero('link');

    expect(animate).not.toHaveBeenCalled();

    rerender(hero('video'));

    expect(animate).toHaveBeenCalledOnce();
    expect(animate.mock.calls[0][0]).toBe(
      screen.getByRole('tabpanel', { name: '本地视频' }),
    );
    expect(animate.mock.calls[0][1]).toMatchObject({ opacity: 0, y: 6 });
    expect(animate.mock.calls[0][2]).toMatchObject({
      duration: 0.16,
      overwrite: 'auto',
      opacity: 1,
      y: 0,
    });
    expect(screen.getByRole('tab', { name: '本地视频' })).toHaveFocus();
  });

  it('renders state changes without a tween when reduced motion is requested', () => {
    mockMotionPreference(true);
    const animate = vi
      .spyOn(gsap, 'fromTo')
      .mockReturnValue({ kill: vi.fn() } as never);
    const { rerender } = renderHero('link');

    rerender(hero('screenplay'));
    render(<MotionReveal>解析结果</MotionReveal>);

    expect(animate).not.toHaveBeenCalled();
    expect(screen.getByRole('tabpanel', { name: '剧本文档' })).toBeVisible();
    expect(screen.getByText('解析结果')).toBeVisible();
  });

  it('finishes an active reveal when motion is reduced without replaying it later', () => {
    const preference = mockMotionPreference(false);
    const tween = { kill: vi.fn() };
    const animate = vi.spyOn(gsap, 'fromTo').mockReturnValue(tween as never);
    const clearStyles = vi.spyOn(gsap, 'set');
    const { unmount } = render(<MotionReveal>解析结果</MotionReveal>);
    const target = screen.getByText('解析结果');

    expect(animate).toHaveBeenCalledOnce();
    expect(preference.listenerCount()).toBe(1);

    act(() => preference.setReduced(true));
    act(() => preference.setReduced(false));

    expect(tween.kill).toHaveBeenCalledOnce();
    expect(clearStyles).toHaveBeenCalledWith(
      target,
      expect.objectContaining({
        clearProps: 'transform,opacity,willChange',
      }),
    );
    expect(animate).toHaveBeenCalledOnce();

    unmount();
    expect(tween.kill).toHaveBeenCalledTimes(2);
    expect(preference.listenerCount()).toBe(0);
  });
});

function renderHero(mode: IntakeMode) {
  return render(hero(mode));
}

function hero(mode: IntakeMode) {
  return (
    <ContentIntakeHero
      disabled={false}
      linkForm={<div>链接表单</div>}
      mode={mode}
      onModeChange={() => undefined}
      screenplayForm={<div>剧本表单</div>}
      videoForm={<div>视频表单</div>}
    />
  );
}

function mockMotionPreference(initialValue: boolean) {
  const query = '(prefers-reduced-motion: reduce)';
  const listeners = new Set<(event: MediaQueryListEvent) => void>();
  let reduceMotion = initialValue;

  vi.spyOn(window, 'matchMedia').mockImplementation(
    (requestedQuery) =>
      ({
        matches: requestedQuery === query ? reduceMotion : false,
        media: requestedQuery,
        onchange: null,
        addEventListener: (
          eventName: string,
          listener: EventListenerOrEventListenerObject,
        ) => {
          if (
            requestedQuery === query &&
            eventName === 'change' &&
            typeof listener === 'function'
          ) {
            listeners.add(listener as (event: MediaQueryListEvent) => void);
          }
        },
        addListener: vi.fn(),
        dispatchEvent: vi.fn(() => true),
        removeEventListener: (
          eventName: string,
          listener: EventListenerOrEventListenerObject,
        ) => {
          if (eventName === 'change' && typeof listener === 'function') {
            listeners.delete(listener as (event: MediaQueryListEvent) => void);
          }
        },
        removeListener: vi.fn(),
      }) as MediaQueryList,
  );

  return {
    listenerCount: () => listeners.size,
    setReduced(value: boolean) {
      reduceMotion = value;
      const event = { matches: value, media: query } as MediaQueryListEvent;
      for (const listener of listeners) listener(event);
    },
  };
}
