import { sessionGeneration } from '@/lib/session-events';

export function privateQueryKey(resource: string, ...parameters: unknown[]) {
  return ['private', sessionGeneration(), resource, ...parameters] as const;
}
