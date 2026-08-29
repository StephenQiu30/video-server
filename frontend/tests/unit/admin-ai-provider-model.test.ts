import { describe, expect, it } from 'vitest';

import {
  providerEngineDefaults,
  providerEngineLabel,
} from '@/components/admin/admin-ai-providers/model';

describe('AI Provider editor model', () => {
  it('keeps local Codex as the default route', () => {
    expect(providerEngineDefaults('codex')).toEqual({
      authMode: 'host_login',
      baseUrl: '',
      model: 'gpt-5.6-sol',
    });
  });

  it('configures DeepSeek through the Web API profile', () => {
    expect(providerEngineDefaults('deepseek')).toEqual({
      authMode: 'api_key',
      baseUrl: 'https://api.deepseek.com',
      model: 'deepseek-v4-flash-vision-exp',
    });
    expect(providerEngineLabel('deepseek')).toBe('DeepSeek');
  });
});
