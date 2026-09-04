import { describe, expect, it } from 'vitest';

import { validateRegistration } from '@/components/auth/register-form-model';
import { normalizeUsername, usernameLength } from '@/lib/username';

const validValues = {
  confirmPassword: 'strong-password',
  email: 'user@example.com',
  password: 'strong-password',
  username: 'layout-user',
};

describe('registration form validation', () => {
  it('accepts a conventional public email address', () => {
    expect(validateRegistration(validValues)).toEqual({});
  });

  it.each([
    'user@example.invalid',
    'user@localhost',
    'user@-example.com',
    'user@example-.com',
  ])('rejects an email the server will not accept: %s', (email) => {
    expect(validateRegistration({ ...validValues, email })).toMatchObject({
      email: '请输入有效的邮箱地址',
    });
  });

  it.each(['layout user', 'layout@user', 'layout/user'])(
    'rejects a username the server will not accept: %s',
    (username) => {
      expect(validateRegistration({ ...validValues, username })).toMatchObject({
        username: '用户名仅支持字母、数字、中文以及 _-. 字符',
      });
    },
  );

  it('normalizes full-width username characters like the server', () => {
    expect(normalizeUsername('  ｌａｙｏｕｔ－ｕｓｅｒ  ')).toBe('layout-user');
    expect(
      validateRegistration({ ...validValues, username: '布局用户_01' }),
    ).toEqual({});
  });

  it('counts supplementary Unicode letters as one server-side character', () => {
    expect(usernameLength('𠀀a')).toBe(2);
    expect(validateRegistration({ ...validValues, username: '𠀀a' })).toEqual(
      {},
    );
  });
});
