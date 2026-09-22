'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  type ReactNode,
  useEffect,
  useState,
  useSyncExternalStore,
} from 'react';
import {
  onSessionGenerationChanged,
  sessionGeneration,
} from '@/lib/session-events';

export function QueryProvider({ children }: { children: ReactNode }) {
  const generation = useSyncExternalStore(
    onSessionGenerationChanged,
    sessionGeneration,
    () => 0,
  );
  // A new identity receives a new provider/cache before descendants render.
  // Client construction is local to this root, never shared by SSR requests.
  return <IdentityQueries key={generation}>{children}</IdentityQueries>;
}

function IdentityQueries({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            gcTime: 5 * 60_000,
            retry: false,
            refetchOnWindowFocus: false,
            refetchOnReconnect: true,
          },
          mutations: { retry: false },
        },
      }),
  );
  useEffect(
    () => () => {
      void client.cancelQueries();
      client.clear();
    },
    [client],
  );
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
