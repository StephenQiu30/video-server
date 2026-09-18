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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<API.UserResponse>();
  const [loading, setLoading] = useState(true);
  const initialized = useRef(false);
  const setUser = useCallback<
    Dispatch<SetStateAction<API.UserResponse | undefined>>
  >((value) => {
    taskSocket.reset();
    setUserState(value);
  }, []);

  const refreshUser = useCallback(async () => {
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
    void refreshUser();
  }, [refreshUser]);

  const signOut = useCallback(async () => {
    try {
      await logout();
    } catch {
      // A stale server session is still a successful local sign-out.
    } finally {
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
