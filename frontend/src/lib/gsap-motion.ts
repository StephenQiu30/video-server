import { gsap } from '@/lib/gsap-client';
import {
  collectMotionTargets,
  createMotionCleanup,
  createRevealMetrics,
  REDUCED_MOTION_QUERY,
  REVEAL_CLEAR_PROPS,
} from '@/lib/gsap-motion-utils';

type StagedRevealOptions = {
  distance?: number;
  duration?: number;
  maxStagger?: number;
  selector: string;
};

export function createStagedRevealTimeline(
  scope: HTMLElement,
  { distance, duration, maxStagger = 0.1, selector }: StagedRevealOptions,
) {
  const preference = window.matchMedia(REDUCED_MOTION_QUERY);
  const targets = collectMotionTargets(scope, selector);
  if (targets.length === 0) return undefined;

  if (preference.matches) {
    gsap.set(targets, { clearProps: REVEAL_CLEAR_PROPS });
    return undefined;
  }

  const metrics = createRevealMetrics(targets.length);
  const distribute = gsap.utils.distribute({
    amount: Math.min(metrics.stagger, maxStagger),
    ease: 'power1.out',
    from: 'start',
  });
  const timeline = gsap.timeline();

  targets.forEach((target, index, collection) => {
    timeline.fromTo(
      target,
      {
        opacity: 0,
        willChange: 'transform, opacity',
        y: distance ?? metrics.distance,
      },
      {
        opacity: 1,
        clearProps: REVEAL_CLEAR_PROPS,
        duration: duration ?? metrics.duration,
        ease: 'power2.out',
        immediateRender: true,
        y: 0,
      },
      distribute(index, target, collection),
    );
  });

  return createMotionCleanup(preference, timeline, targets);
}

/**
 * Creates the small reveal used for client-only result/state transitions.
 * Call this from a scoped useGSAP callback so the tween is tracked by the
 * component context. The returned cleanup also handles a live preference
 * change before the component is unmounted.
 */
export function createRevealTween(target: HTMLElement, duration: number) {
  const reducedMotion = window.matchMedia(REDUCED_MOTION_QUERY);
  if (reducedMotion.matches) return undefined;

  const [element] = gsap.utils.toArray<HTMLElement>(target);
  if (!element) return undefined;

  const tween = gsap.fromTo(
    element,
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
