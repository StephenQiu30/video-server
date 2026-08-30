'use client';

import { useGSAP } from '@gsap/react';
import gsap from 'gsap';
import { type ReactNode, useRef } from 'react';

gsap.registerPlugin(useGSAP);

const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';

export function MotionReveal({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const rootRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const target = rootRef.current;
      if (!target) return;

      const reducedMotion = window.matchMedia(REDUCED_MOTION_QUERY);
      if (reducedMotion.matches) return;

      const tween = gsap.fromTo(
        target,
        { opacity: 0, y: 6, willChange: 'transform, opacity' },
        {
          clearProps: 'transform,opacity,willChange',
          duration: 0.2,
          ease: 'power2.out',
          opacity: 1,
          y: 0,
        },
      );
      const finishImmediately = (event: MediaQueryListEvent) => {
        if (!event.matches) return;
        tween.kill();
        gsap.set(target, { clearProps: 'transform,opacity,willChange' });
      };
      reducedMotion.addEventListener('change', finishImmediately);

      return () => {
        reducedMotion.removeEventListener('change', finishImmediately);
        tween.kill();
      };
    },
    { scope: rootRef },
  );

  return (
    <div className={className} ref={rootRef}>
      {children}
    </div>
  );
}
