import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { useState } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DownloadWorkspace from '@/components/intake/download-workspace';
import { PUBLIC_INPUT_REQUIRED } from '@/components/intake/public-input';
import { QuickParseDialog } from '@/components/intake/quick-parse-dialog';
import { TooltipProvider } from '@/components/ui/tooltip';
import { intentFixture } from '../fixtures/intent-fixtures';
import { httpRequests, mockHttpResponses } from '../helpers/http';
import { render } from '../helpers/query-render';

const navigation = vi.hoisted(() => ({ pathname: '/history', push: vi.fn() }));

vi.mock('@/components/auth/auth-provider', async (importOriginal) => ({
  ...(await importOriginal()),
  useAuth: () => ({ user: { id: 'quick-parse-owner', role: 'user' } }),
}));
vi.mock('next/navigation', () => ({
  usePathname: () => navigation.pathname,
  useRouter: () => ({ push: navigation.push }),
}));

function Harness() {
  const [home, setHome] = useState(false);
  return (
    <TooltipProvider>
      <QuickParseDialog />
      <button onClick={() => setHome(true)} type="button">
        挂载首页
      </button>
      {home ? <DownloadWorkspace /> : null}
    </TooltipProvider>
  );
}

describe('quick parse', () => {
  beforeEach(() => {
    navigation.pathname = '/history';
    navigation.push.mockReset();
    window.history.replaceState({}, '', '/history');
  });

  it('opens with ⌘K and hands one parse request to the homepage', async () => {
    const shareText = '看看这个视频 https://example.com/video';
    mockHttpResponses(
      intentFixture({ status: 'resolving', inspection_id: null }),
    );
    render(<Harness />);

    fireEvent.keyDown(document, { key: 'k', metaKey: true });
    const dialog = screen.getByRole('dialog', { name: '快速解析' });
    const input = within(dialog).getByRole('combobox', {
      name: '快速解析媒体地址',
    });
    fireEvent.change(input, { target: { value: shareText } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(navigation.push).toHaveBeenCalledWith('/');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '挂载首页' }));
    await waitFor(() =>
      expect(
        httpRequests().filter((request) => request.method === 'POST'),
      ).toHaveLength(1),
    );
    expect(httpRequests()[0].data).toEqual({ input: shareText });
    expect(screen.getByRole('textbox', { name: '公开视频地址' })).toHaveValue(
      shareText,
    );
  });

  it('supports Ctrl+K and keeps blank input in the dialog', () => {
    render(<Harness />);
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    const dialog = screen.getByRole('dialog', { name: '快速解析' });
    fireEvent.click(within(dialog).getByRole('option', { name: /解析媒体/ }));

    expect(within(dialog).getByRole('alert')).toHaveTextContent(
      PUBLIC_INPUT_REQUIRED,
    );
    expect(navigation.push).not.toHaveBeenCalled();
    expect(httpRequests()).toHaveLength(0);
  });

  it('keeps a multiline share message intact when pasted into CommandInput', () => {
    render(<Harness />);
    fireEvent.keyDown(document, { key: 'k', metaKey: true });
    const input = screen.getByRole('combobox', {
      name: '快速解析媒体地址',
    });
    fireEvent.paste(input, {
      clipboardData: {
        getData: () => '看看这个视频\nhttps://example.com/video',
      },
    });

    expect(input).toHaveValue('看看这个视频 https://example.com/video');
  });
});
