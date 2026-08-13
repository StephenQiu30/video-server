'use client';

import { ArrowRightIcon, WarningCircleIcon } from '@phosphor-icons/react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { type FormEvent, useEffect, useRef, useState } from 'react';

import { AuthField, AuthPageFrame } from '@/components/app-shell';
import { useAuth } from '@/components/auth-provider';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { FieldGroup } from '@/components/ui/field';
import { InputGroupInput } from '@/components/ui/input-group';
import { Spinner } from '@/components/ui/spinner';
import { displayError, login } from '@/services/auth';
import { authRedirect } from '@/utils/authRedirect';

type FieldErrors = Partial<Record<'email' | 'password', string>>;

export function LoginView() {
  const { user, loading, setUser } = useAuth();
  const [redirect, setRedirect] = useState('/');
  const [search, setSearch] = useState('');
  const [errors, setErrors] = useState<FieldErrors>({});
  const [errorMessage, setErrorMessage] = useState<string>();
  const [submitting, setSubmitting] = useState(false);
  const errorRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    const currentSearch = window.location.search;
    const destination = authRedirect(currentSearch);
    setRedirect(destination);
    setSearch(currentSearch);
    if (!loading && user) router.replace(destination);
  }, [loading, router, user]);

  useEffect(() => {
    if (errorMessage) errorRef.current?.focus();
  }, [errorMessage]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const email = String(data.get('email') ?? '').trim();
    const password = String(data.get('password') ?? '');
    const nextErrors = validateLogin(email, password);
    setErrors(nextErrors);
    setErrorMessage(undefined);
    if (Object.keys(nextErrors).length) return;

    setSubmitting(true);
    try {
      const currentUser = await login({ email, password });
      setUser(currentUser);
      router.replace(redirect);
    } catch (error) {
      setErrorMessage(displayError(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthPageFrame
      description="回到你的下载记录，继续处理有权使用的公开视频。"
      title="登录，继续下载。"
      titleId="login-title"
    >
      <form
        aria-busy={submitting}
        className="space-y-7"
        noValidate
        onSubmit={handleSubmit}
      >
        {errorMessage ? (
          <Alert ref={errorRef} tabIndex={-1} variant="destructive">
            <WarningCircleIcon aria-hidden />
            <AlertDescription>{errorMessage}</AlertDescription>
          </Alert>
        ) : null}
        <FieldGroup className="gap-5">
          <AuthField
            error={errors.email}
            idPrefix="login"
            label="邮箱地址"
            name="email"
          >
            <InputGroupInput
              aria-describedby={errors.email ? 'email-error' : undefined}
              aria-invalid={Boolean(errors.email)}
              autoComplete="email"
              className="h-full"
              id="login-email"
              name="email"
              placeholder="name@example.com"
              type="email"
            />
          </AuthField>
          <AuthField
            error={errors.password}
            idPrefix="login"
            label="密码"
            name="password"
          >
            <InputGroupInput
              aria-describedby={errors.password ? 'password-error' : undefined}
              aria-invalid={Boolean(errors.password)}
              autoComplete="current-password"
              className="h-full"
              id="login-password"
              minLength={8}
              name="password"
              placeholder="至少 8 个字符"
              type="password"
            />
          </AuthField>
        </FieldGroup>
        <Button
          className="h-12 w-full text-[15px]"
          disabled={loading || submitting}
          size="lg"
          type="submit"
        >
          {submitting ? (
            <Spinner
              aria-hidden
              className="motion-reduce:animate-none"
              role="presentation"
            />
          ) : null}
          {submitting ? '正在登录…' : '登录'}
          {!submitting ? (
            <ArrowRightIcon aria-hidden className="size-4" />
          ) : null}
        </Button>
      </form>
      <p className="mt-7 text-sm text-muted-foreground">
        还没有账号？{' '}
        <Link
          className="focus-ring rounded-sm font-medium text-foreground underline underline-offset-4 decoration-foreground/25 hover:decoration-foreground"
          href={`/user/register${search}`}
        >
          创建账号
        </Link>
      </p>
    </AuthPageFrame>
  );
}

function validateLogin(email: string, password: string): FieldErrors {
  const errors: FieldErrors = {};
  if (!email) errors.email = '请输入邮箱地址';
  else if (!/^\S+@\S+\.\S+$/u.test(email))
    errors.email = '请输入有效的邮箱地址';
  if (!password) errors.password = '请输入密码';
  else if (password.length < 8) errors.password = '密码至少需要 8 个字符';
  return errors;
}

export default LoginView;
