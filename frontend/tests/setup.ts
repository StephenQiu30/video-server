import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { history, request } from '@umijs/max';
import { afterEach, beforeEach, vi } from 'vitest';

vi.mock('@umijs/max', () => ({
  history: { push: vi.fn() },
  request: vi.fn(),
  useParams: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(request).mockReset();
  vi.mocked(history.push).mockReset();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

Object.defineProperty(globalThis, 'ResizeObserver', {
  configurable: true,
  writable: true,
  value: ResizeObserverMock,
});
