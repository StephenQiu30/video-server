import { useEffect, useMemo } from 'react';

/** Invalidates pending responses on target changes, mutations and unmount. */
export function useRequestScope(key: string) {
  const scope = useMemo(() => {
    let active = true;
    let epoch = 0;
    let sequence = 0;
    return {
      activate() {
        active = true;
      },
      dispose() {
        active = false;
        epoch++;
      },
      invalidate() {
        epoch++;
      },
      capture() {
        const generation = epoch;
        const request = ++sequence;
        const current = () => active && generation === epoch;
        return { current, latest: () => current() && request === sequence };
      },
      key,
    };
  }, [key]);
  useEffect(() => {
    scope.activate();
    return () => scope.dispose();
  }, [scope]);
  return scope;
}
