import { describe, expect, it } from 'vitest';

import { validateRegistration } from '@/components/register-form-model';

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
});
