'use client';

import {
  ArrowRightIcon,
  EnvelopeSimpleIcon,
  LockKeyIcon,
  SpinnerGapIcon,
  WarningCircleIcon,
} from '@phosphor-icons/react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { type FormEvent, useEffect, useRef, useState } from 'react';

import { AuthField, AuthPageFrame } from '@/components/app-shell';
import { useAuth } from '@/components/auth-provider';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
      description="继续解析、下载和管理你有权处理的公开视频。"
      eyebrow="欢迎回来"
      title="登录帧取"
      titleId="login-title"
    >
      <form
        aria-busy={submitting}
        className="mt-9 space-y-5"
        noValidate
        onSubmit={handleSubmit}
      >
        {errorMessage ? (
          <Alert ref={errorRef} tabIndex={-1} variant="destructive">
            <WarningCircleIcon aria-hidden />
            <AlertDescription>{errorMessage}</AlertDescription>
          </Alert>
        ) : null}
        <AuthField
          error={errors.email}
          icon={<EnvelopeSimpleIcon aria-hidden />}
          idPrefix="login"
          label="邮箱地址"
          name="email"
        >
          <Input
            aria-describedby={errors.email ? 'email-error' : undefined}
            aria-invalid={Boolean(errors.email)}
            autoComplete="email"
            className="pl-11"
            id="login-email"
            name="email"
            placeholder="name@example.com"
            type="email"
          />
        </AuthField>
        <AuthField
          error={errors.password}
          icon={<LockKeyIcon aria-hidden />}
          idPrefix="login"
          label="密码"
          name="password"
        >
          <Input
            aria-describedby={errors.password ? 'password-error' : undefined}
            aria-invalid={Boolean(errors.password)}
            autoComplete="current-password"
            className="pl-11"
            id="login-password"
            minLength={8}
            name="password"
            placeholder="至少 8 个字符"
            type="password"
          />
        </AuthField>
        <Button
          className="h-12 w-full text-[15px]"
          disabled={loading || submitting}
          size="lg"
          type="submit"
        >
          {submitting ? (
            <SpinnerGapIcon
              aria-hidden
              className="size-5 animate-spin motion-reduce:animate-none"
            />
          ) : null}
          {submitting ? '正在登录…' : '登录'}
          {!submitting ? (
            <ArrowRightIcon aria-hidden className="size-4" />
          ) : null}
        </Button>
      </form>
      <p className="mt-7 text-center text-sm text-muted-foreground">
        还没有账号？{' '}
        <Link
          className="focus-ring rounded text-primary hover:underline"
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
