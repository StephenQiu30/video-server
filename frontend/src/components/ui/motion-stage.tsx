import { Slot } from 'radix-ui';
import type { ComponentProps } from 'react';

type MotionStageProps = ComponentProps<typeof Slot.Root> & {
  stage: 'header' | 'home';
};

export function MotionStage({ stage, ...props }: MotionStageProps) {
  return <Slot.Root data-motion-stage={stage} {...props} />;
}
