'use client';

import {
  createContext,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
  useContext,
  useMemo,
  useState,
} from 'react';
import type { IntakeMode } from '@/components/intake/content-intake-hero';

type IntakeDraft = {
  input: string;
  mode: IntakeMode;
  declaredOrigin: API.DeclaredOrigin;
  setInput: Dispatch<SetStateAction<string>>;
  setMode: Dispatch<SetStateAction<IntakeMode>>;
  setDeclaredOrigin: Dispatch<SetStateAction<API.DeclaredOrigin>>;
  attempt: ParseAttempt | null;
  setAttempt: Dispatch<SetStateAction<ParseAttempt | null>>;
};

export type ParseAttempt = {
  key?: string;
  id?: string;
  input: string | null;
  submitting: boolean;
};

const IntakeDraftContext = createContext<IntakeDraft | null>(null);

// Mounted inside the identity-keyed query root. Private share text lives only
// in this application session, never in a URL, browser storage or SSR singleton.
export function IntakeDraftProvider({ children }: { children: ReactNode }) {
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<IntakeMode>('link');
  const [declaredOrigin, setDeclaredOrigin] =
    useState<API.DeclaredOrigin>('user_file');
  const [attempt, setAttempt] = useState<ParseAttempt | null>(null);
  const value = useMemo(
    () => ({
      input,
      mode,
      declaredOrigin,
      setInput,
      setMode,
      setDeclaredOrigin,
      attempt,
      setAttempt,
    }),
    [input, mode, declaredOrigin, attempt],
  );
  return <IntakeDraftContext value={value}>{children}</IntakeDraftContext>;
}

export function useIntakeDraft() {
  const draft = useContext(IntakeDraftContext);
  if (!draft) throw new Error('IntakeDraftProvider is required');
  return draft;
}
