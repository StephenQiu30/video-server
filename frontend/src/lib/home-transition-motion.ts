import { gsap } from '@/lib/gsap-client';
import {
  collectMotionTargets,
  createMotionCleanup,
  createRevealMetrics,
  REDUCED_MOTION_QUERY,
  REVEAL_CLEAR_PROPS,
} from '@/lib/gsap-motion-utils';

export function createSessionRestoreTimeline(scope: HTMLElement) {
  const preference = window.matchMedia(REDUCED_MOTION_QUERY);
  const line = collectMotionTargets(scope, '[data-home-boot-line]');
  if (line.length === 0) return undefined;

  if (preference.matches) {
    gsap.set(line, { scaleX: 1, transformOrigin: 'left center' });
    return undefined;
  }

  gsap.set(line, {
    scaleX: 0.2,
    transformOrigin: 'left center',
    willChange: 'transform, opacity',
  });
  const timeline = gsap.timeline({ repeat: -1, yoyo: true }).to(line, {
    duration: 0.72,
    ease: 'power2.inOut',
    opacity: 0.58,
    scaleX: 0.82,
  });

  return createMotionCleanup(preference, timeline, line);
}

export function createHomeResolutionTimeline(
  scope: HTMLElement,
  onComplete: () => void,
) {
  const preference = window.matchMedia(REDUCED_MOTION_QUERY);
  const bootLayer = collectMotionTargets(scope, '[data-home-boot]');
  const bootCopy = collectMotionTargets(scope, '[data-home-boot-copy]');
  const bootLine = collectMotionTargets(scope, '[data-home-boot-line]');
  const content = collectMotionTargets(scope, '[data-home-reveal]');
  const animatedTargets = [...bootLayer, ...bootCopy, ...bootLine, ...content];
  let finished = false;
  const finish = () => {
    if (finished) return;
    finished = true;
    onComplete();
  };

  if (preference.matches) {
    gsap.set(animatedTargets, { clearProps: REVEAL_CLEAR_PROPS });
    finish();
    return undefined;
  }

  const metrics = createRevealMetrics(content.length);
  const distribute = gsap.utils.distribute({
    amount: metrics.stagger,
    ease: 'power1.out',
    from: 'start',
  });
  if (content.length > 0) {
    gsap.set(content, {
      opacity: 0,
      willChange: 'transform, opacity',
      y: metrics.distance,
    });
  }
  gsap.set(bootLayer, { willChange: 'opacity' });

  const timeline = gsap.timeline({ onComplete: finish });
  timeline
    .to(
      bootCopy,
      {
        opacity: 0,
        duration: 0.12,
        ease: 'power1.in',
        y: -4,
      },
      0,
    )
    .to(bootLine, { duration: 0.16, ease: 'power2.inOut', scaleX: 1 }, 0)
    .to(bootLayer, { opacity: 0, duration: 0.16, ease: 'power1.out' }, 0.04);

  content.forEach((target, index, collection) => {
    timeline.fromTo(
      target,
      {
        opacity: 0,
        willChange: 'transform, opacity',
        y: metrics.distance,
      },
      {
        opacity: 1,
        clearProps: REVEAL_CLEAR_PROPS,
        duration: metrics.duration,
        ease: 'power2.out',
        immediateRender: true,
        y: 0,
      },
      0.06 + distribute(index, target, collection),
    );
  });

  return createMotionCleanup(preference, timeline, animatedTargets, finish);
}
