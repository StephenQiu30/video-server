import { gsap } from '@/lib/gsap-client';

export const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';
export const REVEAL_CLEAR_PROPS = 'transform,opacity,willChange';

export function collectMotionTargets(scope: HTMLElement, selector: string) {
  const select = gsap.utils.selector(scope);
  return gsap.utils.toArray<HTMLElement>(select(selector));
}

export function createRevealMetrics(targetCount: number) {
  const viewport = gsap.utils.clamp(320, 1440, window.innerWidth);

  return {
    distance: Math.round(gsap.utils.mapRange(320, 1440, 8, 14, viewport)),
    duration: gsap.utils.clamp(0.16, 0.2, 0.15 + targetCount * 0.01),
    stagger: gsap.utils.clamp(0, 0.1, (targetCount - 1) * 0.025),
  };
}

export function createMotionCleanup(
  preference: MediaQueryList,
  animation: gsap.core.Animation,
  targets: HTMLElement[],
  finish?: () => void,
) {
  const finishImmediately = (event: MediaQueryListEvent) => {
    if (!event.matches) return;
    animation.kill();
    gsap.set(targets, { clearProps: REVEAL_CLEAR_PROPS });
    finish?.();
  };
  preference.addEventListener('change', finishImmediately);

  return () => {
    preference.removeEventListener('change', finishImmediately);
    animation.kill();
    gsap.set(targets, { clearProps: REVEAL_CLEAR_PROPS });
  };
}
