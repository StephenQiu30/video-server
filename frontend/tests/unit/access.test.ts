import { describe, expect, it } from 'vitest';

import access from '@/access';
import type { InitialState } from '@/app';

function state(role: API.UserRole): InitialState {
  return {
    currentUser: {
      id: '11111111-1111-4111-8111-111111111111',
      username: 'video_user',
      email: 'user@example.com',
      role,
      created_at: '2026-08-09T10:00:00Z',
      updated_at: '2026-08-09T10:00:00Z',
    },
    fetchCurrentUser: async () => undefined,
  };
}

describe('role access', () => {
  it('only exposes administrator routes to administrators', () => {
    expect(access(state('admin')).canAdmin).toBe(true);
    expect(access(state('user')).canAdmin).toBe(false);
    expect(access(undefined).canAdmin).toBe(false);
  });
});
