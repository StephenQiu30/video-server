import { describe, expect, it } from 'vitest';

import {
  hasPublicInput,
  isWeChatArticleInput,
  PUBLIC_INPUT_REQUIRED,
} from '@/utils/public-input';

describe('public input', () => {
  it('only rejects blank input locally', () => {
    expect(hasPublicInput(' https://media.example/video ')).toBe(true);
    expect(hasPublicInput('not-a-url')).toBe(true);
    expect(hasPublicInput('')).toBe(false);
    expect(PUBLIC_INPUT_REQUIRED).toContain('分享文案');
  });

  it('detects WeChat article input without canonicalizing it', () => {
    const shareMessage =
      '打开链接 https://mp.weixin.qq.com/s/article_123\n复制本条消息';

    expect(isWeChatArticleInput(shareMessage)).toBe(true);
    expect(isWeChatArticleInput('https://media.example/video')).toBe(false);
  });
});
