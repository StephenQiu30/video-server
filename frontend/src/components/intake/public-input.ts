export const PUBLIC_INPUT_REQUIRED = '请输入公开链接或完整分享文案。';

const WECHAT_ARTICLE_INPUT_PATTERN =
  /https?:\/\/mp\.weixin\.qq\.com(?:[/?#\s]|$)/iu;

export function hasPublicInput(value: string): boolean {
  return value.trim().length > 0;
}

/** The server owns public-input extraction and URL policy. */
export function isWeChatArticleInput(value: string): boolean {
  return WECHAT_ARTICLE_INPUT_PATTERN.test(value);
}
