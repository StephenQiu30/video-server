import { gsap } from '@/lib/gsap-client';

const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';
const REVEAL_CLEAR_PROPS = 'transform,opacity,willChange';

/**
 * Creates the small reveal used for client-only result/state transitions.
 * Call this from a scoped useGSAP callback so the tween is tracked by the
 * component context. The returned cleanup also handles a live preference
 * change before the component is unmounted.
 */
export function createRevealTween(target: HTMLElement, duration: number) {
  const reducedMotion = window.matchMedia(REDUCED_MOTION_QUERY);
  if (reducedMotion.matches) return undefined;

  const tween = gsap.fromTo(
    target,
    {
      opacity: 0,
      willChange: 'transform, opacity',
      y: 6,
    },
    {
      clearProps: REVEAL_CLEAR_PROPS,
      duration,
      ease: 'power2.out',
      immediateRender: true,
      overwrite: 'auto',
      opacity: 1,
      y: 0,
    },
  );

  const finishImmediately = (event: MediaQueryListEvent) => {
    if (!event.matches) return;
    tween.kill();
    gsap.set(target, { clearProps: REVEAL_CLEAR_PROPS });
  };
  reducedMotion.addEventListener('change', finishImmediately);

  return () => {
    reducedMotion.removeEventListener('change', finishImmediately);
    tween.kill();
  };
}
