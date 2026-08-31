import { describe, expect, it } from 'vitest';

import { normalizeMediaUrl, validateMediaUrl } from '@/utils/validation';
import { reportedDouyinShareMessage } from '../fixtures/download-fixtures';

describe('validateMediaUrl', () => {
  it('accepts public-looking HTTP(S) URLs', () => {
    expect(validateMediaUrl('https://media.example/video')).toBeNull();
    expect(validateMediaUrl('http://media.example/video')).toBeNull();
  });

  it('rejects invalid schemes, credentials, and malformed values', () => {
    expect(validateMediaUrl('file:///tmp/video')).toBeTruthy();
    expect(
      validateMediaUrl('https://user:pass@example.com/video'),
    ).toBeTruthy();
    expect(validateMediaUrl('not-a-url')).toBeTruthy();
    expect(validateMediaUrl('')).toBeTruthy();
  });

  it('extracts the only URL from a copied Douyin share message', () => {
    const shareMessage =
      '5.35 PKj:/ :7pm 04/15 R@k.ca “不追求那个” #于谦#郭麒麟#阎鹤祥#相声 https://v.douyin.com/uLK6Ofbm54k/ 复制此链接，打开Dou音搜索，直接观看视频！';

    expect(normalizeMediaUrl(shareMessage)).toBe(
      'https://v.douyin.com/uLK6Ofbm54k/',
    );
    expect(validateMediaUrl(shareMessage)).toBeNull();
  });

  it('extracts the short link from the reported full Douyin share message', () => {
    expect(normalizeMediaUrl(reportedDouyinShareMessage)).toBe(
      'https://v.douyin.com/Tq0eYJRMYRk/',
    );
    expect(validateMediaUrl(reportedDouyinShareMessage)).toBeNull();
  });

  it('extracts the URL from the reported Chinese Douyin share message', () => {
    const shareMessage =
      '0.53 复制打开抖音，看看【喵了个喵-的图文作品】你笑面如花 真想与你情定香格里拉.# 我与天坛 ' +
      'https://v.douyin.com/Z8wTCSQ-1_g/ M@j.cn EHv:/ 04/10 :3pm';

    expect(normalizeMediaUrl(shareMessage)).toBe(
      'https://v.douyin.com/Z8wTCSQ-1_g/',
    );
  });

  it('removes an ASCII closing parenthesis around a share URL', () => {
    expect(normalizeMediaUrl('(https://v.douyin.com/Z8wTCSQ-1_g/)')).toBe(
      'https://v.douyin.com/Z8wTCSQ-1_g/',
    );
  });

  it('rejects share text containing more than one URL', () => {
    expect(
      normalizeMediaUrl('请看 https://example.com/a 和 https://example.com/b'),
    ).toBeNull();
  });
});
