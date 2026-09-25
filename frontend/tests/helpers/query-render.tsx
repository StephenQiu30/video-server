import {
  type RenderOptions,
  render as renderComponent,
  renderHook as renderReactHook,
} from '@testing-library/react';
import type { ComponentType, ReactElement, ReactNode } from 'react';
import { toast } from 'sonner';
import { IntakeDraftProvider } from '@/components/intake/intake-draft-provider';
import { QueryProvider } from '@/components/layout/query-provider';
import { Toaster } from '@/components/ui/sonner';

function withQueries(Wrapper?: ComponentType<{ children: ReactNode }>) {
  return function TestProviders({ children }: { children: ReactNode }) {
    return (
      <QueryProvider>
        <IntakeDraftProvider>
          {Wrapper ? <Wrapper>{children}</Wrapper> : children}
        </IntakeDraftProvider>
      </QueryProvider>
    );
  };
}

export const render = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'queries'>,
) =>
  renderComponent(ui, {
    ...options,
    wrapper: withQueries(options?.wrapper),
  });

export const renderHook: typeof renderReactHook = (callback, options) =>
  renderReactHook(callback, {
    ...options,
    wrapper: withQueries(options?.wrapper),
  });

/** Match the application root for tests that exercise operation notifications. */
export const renderWithToasts: typeof render = (ui, options) => {
  toast.dismiss();
  return render(
    <>
      {ui}
      <Toaster />
    </>,
    options,
  );
};
