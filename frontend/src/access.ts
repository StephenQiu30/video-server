import type { InitialState } from './app';

export default function access(initialState: InitialState | undefined) {
  return {
    canAdmin: initialState?.currentUser?.role === 'admin',
  };
}
