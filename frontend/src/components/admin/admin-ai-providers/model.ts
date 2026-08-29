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

export function providerEngineDefaults(
  engine: API.AiProviderEngine,
): Pick<AiProviderEditorState, 'authMode' | 'baseUrl' | 'model'> {
  if (engine === 'deepseek') {
    return {
      authMode: 'api_key',
      baseUrl: 'https://api.deepseek.com',
      model: 'deepseek-v4-flash-vision-exp',
    };
  }
  return {
    authMode: 'host_login',
    baseUrl: '',
    model: engine === 'codex' ? 'gpt-5.6-sol' : 'sonnet',
  };
}

export function providerEngineLabel(engine: API.AiProviderEngine): string {
  if (engine === 'codex') return 'Codex';
  if (engine === 'claude') return 'Claude';
  return 'DeepSeek';
}
