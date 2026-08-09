'use client';

import {
  createContext,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { type AuthUser, getCurrentUser, logout } from '@/services/auth';

type AuthContextValue = {
  user?: AuthUser;
  loading: boolean;
  setUser: Dispatch<SetStateAction<AuthUser | undefined>>;
  refreshUser: () => Promise<AuthUser | undefined>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const DESIGN_USER: AuthUser = {
  id: '00000000-0000-4000-8000-000000000009',
  username: '设计预览',
  email: 'preview@example.com',
  role: 'user',
  created_at: '2026-08-09T00:00:00Z',
  updated_at: '2026-08-09T00:00:00Z',
};

function isDesignInspection(): boolean {
  return (
    process.env.NODE_ENV === 'development' &&
    typeof window !== 'undefined' &&
    new URLSearchParams(window.location.search).get('design') === 'inspection'
  );
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser>();
  const [loading, setLoading] = useState(true);
  const designPreview = useRef(false);

  const refreshUser = useCallback(async () => {
    if (designPreview.current) {
      setUser(DESIGN_USER);
      setLoading(false);
      return DESIGN_USER;
    }

    setLoading(true);
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      return currentUser;
    } catch {
      setUser(undefined);
      return undefined;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isDesignInspection()) {
      designPreview.current = true;
      setUser(DESIGN_USER);
      setLoading(false);
      return;
    }
    void refreshUser();
  }, [refreshUser]);

  const signOut = useCallback(async () => {
    try {
      if (!designPreview.current) await logout();
    } catch {
      // A stale server session is still a successful local sign-out.
    } finally {
      designPreview.current = false;
      setUser(undefined);
      setLoading(false);
    }
  }, []);

  const value = useMemo(
    () => ({ user, loading, setUser, refreshUser, signOut }),
    [loading, refreshUser, signOut, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider.');
  return context;
}
