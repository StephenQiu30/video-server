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
  withWebSessionMutation,
} from '@/lib/session-events';
import { taskSocket } from '@/lib/task-socket';

export enum AuthStatusCode {
  Unknown = 'unknown',
  Authenticated = 'authenticated',
  Anonymous = 'anonymous',
}

type AuthContextValue = {
  user?: API.UserResponse;
  loading: boolean;
  status: AuthStatusCode;
  sessionError: string | null;
  setUser: Dispatch<SetStateAction<API.UserResponse | undefined>>;
  refreshUser: () => Promise<API.UserResponse | undefined>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({
  children,
  initialUser,
}: {
  children: ReactNode;
  initialUser?: API.UserResponse | null;
}) {
  // This projection seeds only the first render. Later RSC responses cannot
  // replace an identity already owned by this provider.
  const [user, setUserState] = useState<API.UserResponse | undefined>(
    initialUser ?? undefined,
  );
  const [loading, setLoading] = useState(initialUser === undefined);
  const [status, setStatus] = useState<AuthContextValue['status']>(
    initialUser === undefined
      ? AuthStatusCode.Unknown
      : initialUser
        ? AuthStatusCode.Authenticated
        : AuthStatusCode.Anonymous,
  );
  const [sessionError, setSessionError] = useState<string | null>(null);
  const userRef = useRef<API.UserResponse | undefined>(
    initialUser ?? undefined,
  );
  const identityKnown = useRef(initialUser !== undefined);
  const generation = useRef(0);
  const pending = useRef<Promise<API.UserResponse | undefined> | null>(null);
  const signingOut = useRef(false);
  const logoutPending = useRef(false);
  const channel = useRef<BroadcastChannel | null>(null);
  const maskIdentity = useCallback(() => {
    identityKnown.current = false;
    generation.current += 1;
    pending.current = null;
    advanceSessionGeneration();
    taskSocket.reset();
    userRef.current = undefined;
    setUserState(undefined);
    setStatus(AuthStatusCode.Unknown);
    setSessionError(null);
    setLoading(true);
  }, []);
  const applyUser = useCallback((next: API.UserResponse | undefined) => {
    identityKnown.current = true;
    if (userRef.current?.id !== next?.id) {
      advanceSessionGeneration();
      taskSocket.reset();
    }
    userRef.current = next;
    setUserState(next);
    setStatus(next ? AuthStatusCode.Authenticated : AuthStatusCode.Anonymous);
    setSessionError(null);
    setLoading(false);
  }, []);
  const setUser = useCallback<
    Dispatch<SetStateAction<API.UserResponse | undefined>>
  >(
    (value) => {
      generation.current += 1;
      pending.current = null;
      logoutPending.current = false;
      advanceSessionGeneration();
      channel.current?.postMessage({ type: 'identity-changed' });
      applyUser(typeof value === 'function' ? value(userRef.current) : value);
    },
    [applyUser],
  );

  const sessionExpired = useCallback(() => {
    if (logoutPending.current) return;
    // An anonymous /me response must not invalidate a simultaneous login. Only
    // losing a previously confirmed owner advances the private data generation.
    if (userRef.current) maskIdentity();
    else {
      generation.current += 1;
      pending.current = null;
    }
    applyUser(undefined);
  }, [maskIdentity, applyUser]);

  const signOut = useCallback(async () => {
    if (signingOut.current) return;
    signingOut.current = true;
    logoutPending.current = true;
    maskIdentity();
    channel.current?.postMessage({ type: 'logout-started' });
    const current = generation.current;
    try {
      await withWebSessionMutation(async () => {
        await logout();
        if (current === generation.current) setUser(undefined);
      });
    } catch (reason) {
      if (current === generation.current) {
        setSessionError('退出尚未完成。请恢复连接后重试，当前私密内容已隐藏。');
      }
      throw reason;
    } finally {
      signingOut.current = false;
      if (current === generation.current) setLoading(false);
    }
  }, [maskIdentity, setUser]);

  const refreshUser = useCallback(() => {
    if (signingOut.current) return Promise.resolve(undefined);
    if (logoutPending.current) {
      return signOut().then(
        () => undefined,
        () => undefined,
      );
    }
    if (pending.current) return pending.current;
    const current = generation.current;
    if (!identityKnown.current) setLoading(true);
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
          sessionExpired();
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
  }, [applyUser, sessionExpired, signOut]);

  useEffect(() => {
    const unsubscribe = onSessionExpired(sessionExpired);
    void refreshUser();
    const recover = () => {
      void refreshUser();
    };
    const visibility = () => {
      if (document.visibilityState === 'visible') recover();
    };
    const identityChannel =
      typeof BroadcastChannel === 'undefined'
        ? null
        : new BroadcastChannel('framefetch-identity');
    channel.current = identityChannel;
    if (identityChannel)
      identityChannel.onmessage = (event) => {
        if (event.data?.type === 'logout-started') {
          if (logoutPending.current) return;
          logoutPending.current = true;
          maskIdentity();
          setLoading(false);
          setSessionError('正在其他页面退出登录。如未完成，可重试。');
        } else if (event.data?.type === 'identity-changed') {
          logoutPending.current = false;
          maskIdentity();
          void refreshUser();
        }
      };
    window.addEventListener('online', recover);
    document.addEventListener('visibilitychange', visibility);
    return () => {
      unsubscribe();
      window.removeEventListener('online', recover);
      document.removeEventListener('visibilitychange', visibility);
      identityChannel?.close();
      if (channel.current === identityChannel) channel.current = null;
      generation.current += 1;
      pending.current = null;
    };
  }, [refreshUser, sessionExpired, maskIdentity]);

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
