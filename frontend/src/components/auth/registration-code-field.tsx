'use client';

import { useEffect, useRef, useState } from 'react';
import { sendRegistrationCode as requestRegistrationCode } from '@/api/auth';
import { AuthField } from '@/components/auth/auth-page-frame';
import { isValidEmail } from '@/components/auth/register-form-model';
import { Button } from '@/components/ui/button';
import { InputGroupInput } from '@/components/ui/input-group';
import { displayError } from '@/lib/request-error';

export function RegistrationCodeField({
  email,
  code,
  onCodeChange,
  onSendingChange,
  disabled,
  error,
}: {
  email: string;
  code: string;
  onCodeChange: (code: string) => void;
  onSendingChange: (sending: boolean) => void;
  disabled: boolean;
  error?: string;
}) {
  const [sending, setSending] = useState(false);
  const [until, setUntil] = useState(0);
  const [remaining, setRemaining] = useState(0);
  const [message, setMessage] = useState('');
  const busy = useRef(false);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    const tick = () =>
      setRemaining(Math.max(0, Math.ceil((until - Date.now()) / 1000)));
    tick();
    if (!until) return;
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [until]);

  async function send() {
    if (busy.current || until > Date.now()) return;
    if (!isValidEmail(email.trim())) {
      setMessage('请先输入有效的邮箱地址。');
      return;
    }
    busy.current = true;
    setSending(true);
    onSendingChange(true);
    setMessage('');
    try {
      const result = await requestRegistrationCode({ email: email.trim() });
      if (!mounted.current) return;
      if (!result.email_sent) {
        setMessage('邮件发送未能确认，请稍后重新获取验证码。');
        return;
      }
      onCodeChange('');
      setUntil(Date.now() + (result.retry_after_seconds ?? 60) * 1000);
      setMessage('验证码已发送，10 分钟内有效。未收到时请检查垃圾邮件。');
    } catch (failure) {
      if (mounted.current) setMessage(displayError(failure));
    } finally {
      busy.current = false;
      if (mounted.current) {
        setSending(false);
        onSendingChange(false);
      }
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <AuthField
        idPrefix="register"
        name="verificationCode"
        label="邮箱验证码"
        error={error}
      >
        <InputGroupInput
          id="register-verificationCode"
          name="verificationCode"
          value={code}
          onChange={(event) =>
            onCodeChange(event.target.value.replace(/[^0-9]/g, '').slice(0, 6))
          }
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? 'verificationCode-error' : undefined}
          disabled={disabled}
          className="h-full"
          placeholder="6 位验证码"
        />
      </AuthField>
      <Button
        type="button"
        variant="secondary"
        className="min-h-11"
        disabled={
          disabled || sending || remaining > 0 || !isValidEmail(email.trim())
        }
        onClick={() => void send()}
      >
        {sending
          ? '正在发送…'
          : remaining > 0
            ? `${remaining} 秒后可重发`
            : '获取验证码'}
      </Button>
      <p role="status" className="text-sm text-muted-foreground">
        {message}
      </p>
    </div>
  );
}
