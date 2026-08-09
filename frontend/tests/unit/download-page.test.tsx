import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import DownloadPage from '@/pages/Download';

const runtime = vi.hoisted(() => ({ pageProps: undefined as unknown }));

vi.mock('@ant-design/pro-components', () => ({
  ProForm: ({
    children,
    submitter,
  }: {
    children: ReactNode;
    submitter: { searchConfig: { submitText: string } };
  }) => (
    <form>
      {children}
      <button type="submit">{submitter.searchConfig.submitText}</button>
    </form>
  ),
  ProFormText: ({
    fieldProps,
    label,
    name,
    placeholder,
  }: {
    fieldProps: { 'aria-label'?: string };
    label: string;
    name: string;
    placeholder: string;
  }) => (
    <label>
      {label}
      <input
        aria-label={fieldProps['aria-label']}
        name={name}
        placeholder={placeholder}
      />
    </label>
  ),
  PageContainer: (props: { children: ReactNode }) => {
    runtime.pageProps = props;
    return <>{props.children}</>;
  },
}));

vi.mock('@umijs/max', () => ({
  useNavigate: () => vi.fn(),
}));

describe('DownloadPage', () => {
  it('does not render an empty result card before inspection starts', () => {
    const { container } = render(<DownloadPage />);

    expect(runtime.pageProps).toMatchObject({
      title: '解析下载',
    });
    expect(screen.getByLabelText('公开视频地址')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '解析视频' })).toBeInTheDocument();
    expect(
      screen.queryByText('Universal video downloader'),
    ).not.toBeInTheDocument();
    expect(screen.queryByText('支持：')).not.toBeInTheDocument();
    expect(container.querySelector('.content-wrap')).not.toBeInTheDocument();
    expect(screen.queryByText('等待解析公开视频')).not.toBeInTheDocument();
  });
});
