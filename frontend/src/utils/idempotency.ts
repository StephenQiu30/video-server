import { createUuid } from '@/utils/uuid';

export function createIdempotencyKey(): string {
  return createUuid();
}
