'use client';

import { type ReactNode, useRef } from 'react';

import { useGSAP } from '@/lib/gsap-client';
import { createRevealTween } from '@/lib/gsap-motion';

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

      return createRevealTween(target, 0.2);
    },
    { scope: rootRef },
  );

  return (
    <div className={className} data-slot="motion-reveal" ref={rootRef}>
      {children}
    </div>
  );
}
