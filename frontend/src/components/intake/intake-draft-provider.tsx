'use client';

import {
  createContext,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
  useCallback,
  useContext,
  useMemo,
  useRef,
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
  quickParse: { id: number; input: string } | null;
  requestQuickParse: (input: string) => void;
  clearQuickParse: (id: number) => void;
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
  const [quickParse, setQuickParse] = useState<IntakeDraft['quickParse']>(null);
  const nextQuickParseId = useRef(0);
  const requestQuickParse = useCallback((value: string) => {
    setInput(value);
    setMode('link');
    setQuickParse({ id: ++nextQuickParseId.current, input: value });
  }, []);
  const clearQuickParse = useCallback((id: number) => {
    setQuickParse((current) => (current?.id === id ? null : current));
  }, []);
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
      quickParse,
      requestQuickParse,
      clearQuickParse,
    }),
    [
      input,
      mode,
      declaredOrigin,
      attempt,
      quickParse,
      requestQuickParse,
      clearQuickParse,
    ],
  );
  return <IntakeDraftContext value={value}>{children}</IntakeDraftContext>;
}

export function useIntakeDraft() {
  const draft = useContext(IntakeDraftContext);
  if (!draft) throw new Error('IntakeDraftProvider is required');
  return draft;
}
