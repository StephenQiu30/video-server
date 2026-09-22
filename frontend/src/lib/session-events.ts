// The identity owner advances this generation on login/logout. Requests carry
// it so a response from an old identity cannot invalidate the current one.
let generation = 0;
const listeners = new Set<() => void>();

export function sessionGeneration(): number {
  return generation;
}

export function advanceSessionGeneration(): void {
  generation += 1;
}

export function reportSessionExpired(expectedGeneration: number): void {
  if (expectedGeneration !== generation) return;
  for (const listener of listeners) listener();
}

export function onSessionExpired(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
