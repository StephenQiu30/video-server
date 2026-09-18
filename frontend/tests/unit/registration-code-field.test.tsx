import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { sendRegistrationCode as requestRegistrationCode } from '@/api/auth';
import { RegistrationCodeField } from '@/components/auth/registration-code-field';
import { ApiError } from '@/lib/request-error';

function field(email = 'member@example.com') {
  return render(
    <RegistrationCodeField
      email={email}
      code=""
      onCodeChange={vi.fn()}
      onSendingChange={vi.fn()}
      disabled={false}
    />,
  );
}

describe('registration email proof', () => {
  it('confirms SMTP acceptance and disables resend during the server cooldown', async () => {
    vi.mocked(requestRegistrationCode).mockResolvedValue({
      email_sent: true,
      retry_after_seconds: 60,
      expires_in_seconds: 600,
    });
    field();
    fireEvent.click(screen.getByRole('button', { name: '获取验证码' }));
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('验证码已发送'),
    );
    expect(requestRegistrationCode).toHaveBeenCalledWith({
      email: 'member@example.com',
    });
    expect(
      await screen.findByRole('button', { name: /秒后可重发/ }),
    ).toBeDisabled();
  });
  it('shows a send failure without claiming success', async () => {
    vi.mocked(requestRegistrationCode).mockRejectedValue(
      new ApiError(503, 'email_send_failed', 'Failed', 'Failed'),
    );
    field();
    fireEvent.click(screen.getByRole('button', { name: '获取验证码' }));
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('邮件发送未能确认'),
    );
    expect(screen.getByRole('button', { name: '获取验证码' })).toBeEnabled();
  });
  it('checks the email before sending', async () => {
    vi.mocked(requestRegistrationCode).mockClear();
    field('bad-email');
    fireEvent.click(screen.getByRole('button', { name: '获取验证码' }));
    expect(screen.getByRole('button', { name: '获取验证码' })).toBeDisabled();
    expect(requestRegistrationCode).not.toHaveBeenCalled();
  });
});

vi.mock('@/api/auth', async (original) => ({
  ...(await original<typeof import('@/api/auth')>()),
  sendRegistrationCode: vi.fn(),
}));
