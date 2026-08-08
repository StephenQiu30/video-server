import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';

import { httpClient } from '@/lib/request';

vi.mock('next/navigation', () => ({
  usePathname: vi.fn(() => '/'),
  useRouter: vi.fn(() => ({ push: vi.fn() })),
  useSearchParams: vi.fn(() => new URLSearchParams()),
}));

beforeEach(() => {
  vi.spyOn(httpClient, 'request');
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
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
