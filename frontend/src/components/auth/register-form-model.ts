export type FieldName = 'username' | 'email' | 'password' | 'confirmPassword';

export type FieldErrors = Partial<Record<FieldName, string>>;

export function validateRegistration(
  values: Record<FieldName, string>,
): FieldErrors {
  const errors: FieldErrors = {};
  if (!values.username) errors.username = '请设置用户名';
  else if (values.username.length < 2)
    errors.username = '用户名至少需要 2 个字符';
  else if (values.username.length > 32)
    errors.username = '用户名不能超过 32 个字符';
  if (!values.email) errors.email = '请输入邮箱地址';
  else if (!isValidEmail(values.email)) errors.email = '请输入有效的邮箱地址';
  if (!values.password) errors.password = '请设置密码';
  else if (values.password.length < 8)
    errors.password = '密码至少需要 8 个字符';
  else if (values.password.length > 128)
    errors.password = '密码不能超过 128 个字符';
  if (!values.confirmPassword) errors.confirmPassword = '请再次输入密码';
  else if (values.confirmPassword !== values.password)
    errors.confirmPassword = '两次输入的密码不一致';
  return errors;
}

function isValidEmail(value: string): boolean {
  const parts = value.split('@');
  if (parts.length !== 2) return false;
  const [local, domain] = parts;
  if (!local || local.length > 64 || !domain || domain.length > 253)
    return false;
  if (/\s/u.test(value)) return false;

  const labels = domain.toLowerCase().split('.');
  if (labels.length < 2) return false;
  if (
    labels.some(
      (label) =>
        !label ||
        label.length > 63 ||
        label.startsWith('-') ||
        label.endsWith('-') ||
        !/^[a-z0-9-]+$/u.test(label),
    )
  ) {
    return false;
  }

  const topLevelDomain = labels.at(-1) ?? '';
  return (
    /^[a-z]{2,63}$/u.test(topLevelDomain) &&
    !reservedTopLevelDomains.has(topLevelDomain)
  );
}

const reservedTopLevelDomains = new Set([
  'example',
  'invalid',
  'localhost',
  'test',
]);
