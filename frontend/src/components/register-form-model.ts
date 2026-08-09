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
  else if (!/^\S+@\S+\.\S+$/u.test(values.email))
    errors.email = '请输入有效的邮箱地址';
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
