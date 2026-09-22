import {
  type RenderOptions,
  render as renderComponent,
  renderHook as renderReactHook,
} from '@testing-library/react';
import type { ComponentType, ReactElement, ReactNode } from 'react';
import { QueryProvider } from '@/components/layout/query-provider';

function withQueries(Wrapper?: ComponentType<{ children: ReactNode }>) {
  return function TestProviders({ children }: { children: ReactNode }) {
    return (
      <QueryProvider>
        {Wrapper ? <Wrapper>{children}</Wrapper> : children}
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
