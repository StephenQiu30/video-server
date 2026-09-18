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
import { getCurrentUser, logoutUser as logout } from '@/api/auth';
import { ApiError } from '@/lib/request-error';
import { taskSocket } from '@/lib/task-socket';

type AuthContextValue = {
  user?: API.UserResponse;
  loading: boolean;
  setUser: Dispatch<SetStateAction<API.UserResponse | undefined>>;
  refreshUser: () => Promise<API.UserResponse | undefined>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const DESIGN_USER: API.UserResponse = {
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
  const [user, setUserState] = useState<API.UserResponse>();
  const [loading, setLoading] = useState(true);
  const designPreview = useRef(false);
  const initialized = useRef(false);
  const setUser = useCallback<
    Dispatch<SetStateAction<API.UserResponse | undefined>>
  >((value) => {
    taskSocket.reset();
    setUserState(value);
  }, []);

  const refreshUser = useCallback(async () => {
    if (designPreview.current) {
      setUser(DESIGN_USER);
      setLoading(false);
      return DESIGN_USER;
    }

    if (!initialized.current) setLoading(true);
    try {
      const currentUser = await getCurrentUser({ skipAuthRedirect: true });
      setUser(currentUser);
      return currentUser;
    } catch (reason) {
      if (
        !initialized.current ||
        (reason instanceof ApiError && reason.status === 401)
      ) {
        setUser(undefined);
      }
      return undefined;
    } finally {
      initialized.current = true;
      setLoading(false);
    }
  }, [setUser]);

  useEffect(() => {
    if (isDesignInspection()) {
      designPreview.current = true;
      initialized.current = true;
      setUser(DESIGN_USER);
      setLoading(false);
      return;
    }
    void refreshUser();
  }, [refreshUser, setUser]);

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
  }, [setUser]);

  const value = useMemo(
    () => ({ user, loading, setUser, refreshUser, signOut }),
    [loading, refreshUser, setUser, signOut, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider.');
  return context;
}
