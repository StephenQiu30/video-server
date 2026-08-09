import { describe, expect, it } from 'vitest';

import { authRedirect } from '@/utils/authRedirect';

describe('auth redirect validation', () => {
  it('keeps same-origin application destinations', () => {
    expect(authRedirect('?redirect=%2Fhistory%3Fpage%3D2')).toBe(
      '/history?page=2',
    );
  });

  it('rejects external and recursive auth redirects', () => {
    expect(authRedirect('?redirect=https%3A%2F%2Fexample.com')).toBe('/');
    expect(authRedirect('?redirect=%2F%2Fevil.example')).toBe('/');
    expect(authRedirect('?redirect=%2Fuser%2Flogin')).toBe('/');
  });
});
