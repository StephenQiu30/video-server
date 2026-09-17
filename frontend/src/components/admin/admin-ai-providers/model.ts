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

export const LOCAL_CODEX_PROVIDER_KEY = 'local-codex';

export function isLocalCodexProvider(key: string): boolean {
  return key === LOCAL_CODEX_PROVIDER_KEY;
}

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
  if (engine === 'openrouter' || engine === 'openai') {
    return {
      authMode: 'api_key',
      baseUrl:
        engine === 'openrouter'
          ? 'https://openrouter.ai/api/v1'
          : 'https://api.openai.com/v1',
      model: '',
    };
  }
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
  if (engine === 'openrouter') return 'OpenRouter';
  if (engine === 'openai') return 'OpenAI 兼容 API';
  return 'DeepSeek';
}

export function isDirectApiEngine(engine: API.AiProviderEngine): boolean {
  return (
    engine === 'openrouter' || engine === 'openai' || engine === 'deepseek'
  );
}
