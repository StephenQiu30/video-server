export type AiProviderEditorState = {
  mode: 'create' | 'edit' | null;
  key: string;
  displayName: string;
  engine: API.AiProviderEngine;
  authMode: API.AiProviderAuthMode;
  baseUrl: string;
  model: string;
  apiKey: string;
  credentialConfigured: boolean;
  error: string;
  saving: boolean;
};

export const EMPTY_AI_PROVIDER_EDITOR: AiProviderEditorState = {
  mode: null,
  key: '',
  displayName: '',
  engine: 'codex',
  authMode: 'host_login',
  baseUrl: '',
  model: 'gpt-5.6-sol',
  apiKey: '',
  credentialConfigured: false,
  error: '',
  saving: false,
};
