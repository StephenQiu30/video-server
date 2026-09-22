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
import { ApiError, displayError } from '@/lib/request-error';
import {
  advanceSessionGeneration,
  onSessionExpired,
} from '@/lib/session-events';
import { taskSocket } from '@/lib/task-socket';

type AuthContextValue = {
  user?: API.UserResponse;
  loading: boolean;
  status: 'unknown' | 'authenticated' | 'anonymous';
  sessionError: string | null;
  setUser: Dispatch<SetStateAction<API.UserResponse | undefined>>;
  refreshUser: () => Promise<API.UserResponse | undefined>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<API.UserResponse>();
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<AuthContextValue['status']>('unknown');
  const [sessionError, setSessionError] = useState<string | null>(null);
  const userRef = useRef<API.UserResponse | undefined>(undefined);
  const generation = useRef(0);
  const pending = useRef<Promise<API.UserResponse | undefined> | null>(null);
  const signingOut = useRef(false);
  const applyUser = useCallback((next: API.UserResponse | undefined) => {
    if (userRef.current?.id !== next?.id) {
      advanceSessionGeneration();
      taskSocket.reset();
    }
    userRef.current = next;
    setUserState(next);
    setStatus(next ? 'authenticated' : 'anonymous');
    setSessionError(null);
    setLoading(false);
  }, []);
  const setUser = useCallback<
    Dispatch<SetStateAction<API.UserResponse | undefined>>
  >(
    (value) => {
      generation.current += 1;
      pending.current = null;
      advanceSessionGeneration();
      applyUser(typeof value === 'function' ? value(userRef.current) : value);
    },
    [applyUser],
  );

  const refreshUser = useCallback(() => {
    if (signingOut.current) return Promise.resolve(userRef.current);
    if (pending.current) return pending.current;
    const current = generation.current;
    if (!userRef.current) setLoading(true);
    setSessionError(null);
    const request = (async () => {
      try {
        const next = await getCurrentUser();
        if (current !== generation.current) return userRef.current;
        applyUser(next);
        return next;
      } catch (reason) {
        if (current !== generation.current) return userRef.current;
        if (reason instanceof ApiError && reason.status === 401) {
          setUser(undefined);
        } else {
          setSessionError(displayError(reason));
        }
        return userRef.current;
      } finally {
        if (current === generation.current) setLoading(false);
      }
    })();
    pending.current = request;
    void request.finally(() => {
      if (pending.current === request) pending.current = null;
    });
    return request;
  }, [applyUser, setUser]);

  useEffect(() => {
    const unsubscribe = onSessionExpired(() => setUser(undefined));
    void refreshUser();
    const recover = () => {
      void refreshUser();
    };
    window.addEventListener('online', recover);
    return () => {
      unsubscribe();
      window.removeEventListener('online', recover);
      generation.current += 1;
      pending.current = null;
    };
  }, [refreshUser, setUser]);

  const signOut = useCallback(async () => {
    if (signingOut.current) return;
    signingOut.current = true;
    generation.current += 1;
    const current = generation.current;
    pending.current = null;
    try {
      await logout();
      if (current === generation.current) setUser(undefined);
    } finally {
      signingOut.current = false;
      setLoading(false);
    }
  }, [setUser]);

  const value = useMemo(
    () => ({
      user,
      loading,
      status,
      sessionError,
      setUser,
      refreshUser,
      signOut,
    }),
    [loading, status, sessionError, refreshUser, setUser, signOut, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider.');
  return context;
}
