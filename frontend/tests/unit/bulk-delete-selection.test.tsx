import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import {
  type BulkDeleteOptions,
  BulkDeleteSelection,
  SelectionCell,
  SelectionHead,
} from '@/components/layout/bulk-delete-selection';
import { Table, TableBody, TableHeader, TableRow } from '@/components/ui/table';

function Fixture({ options }: { options: BulkDeleteOptions }) {
  return (
    <BulkDeleteSelection ids={['a', 'b']} options={options}>
      <Table>
        <TableHeader>
          <TableRow>
            <SelectionHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {['a', 'b', 'protected'].map((id) => (
            <TableRow key={id}>
              <SelectionCell id={id} label={id} />
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </BulkDeleteSelection>
  );
}
const options = (): BulkDeleteOptions => ({
  scope: 'page-1',
  disabled: false,
  description: '删除记录。',
  remove: vi.fn().mockResolvedValue(undefined),
  onComplete: vi.fn(),
});
describe('bulk deletion', () => {
  it('excludes protected rows, supports mixed selection and resets on scope change', () => {
    const config = options();
    const view = render(<Fixture options={config} />);
    expect(
      screen.getByRole('checkbox', { name: '选择 protected' }),
    ).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox', { name: '选择 a' }));
    expect(screen.getByRole('checkbox', { name: '全选本页' })).toHaveAttribute(
      'aria-checked',
      'mixed',
    );
    fireEvent.click(screen.getByRole('checkbox', { name: '全选本页' }));
    expect(screen.getByRole('button', { name: '批量删除（2）' })).toBeEnabled();
    view.rerender(<Fixture options={{ ...config, scope: 'page-2' }} />);
    expect(
      screen.getByRole('button', { name: '批量删除（0）' }),
    ).toBeDisabled();
  });
  it('requires confirmation and preserves only failed rows', async () => {
    const config = options();
    config.remove = vi
      .fn()
      .mockResolvedValueOnce(undefined)
      .mockRejectedValueOnce(new Error('无法删除'));
    render(<Fixture options={config} />);
    fireEvent.click(screen.getByRole('checkbox', { name: '全选本页' }));
    fireEvent.click(screen.getByRole('button', { name: '批量删除（2）' }));
    expect(config.remove).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: '确认删除' }));
    await waitFor(() => expect(config.onComplete).toHaveBeenCalledWith(['a']));
    expect(screen.getByRole('checkbox', { name: '选择 a' })).not.toBeChecked();
    expect(screen.getByRole('checkbox', { name: '选择 b' })).toBeChecked();
    expect(
      screen.getByText('部分项目删除失败，已保留选择'),
    ).toBeInTheDocument();
  });
  it('stops submitting further deletes when the page unmounts', async () => {
    let resolve!: () => void;
    const config = options();
    config.remove = vi.fn(
      () =>
        new Promise<void>((r) => {
          resolve = r;
        }),
    );
    const view = render(<Fixture options={config} />);
    fireEvent.click(screen.getByRole('checkbox', { name: '全选本页' }));
    fireEvent.click(screen.getByRole('button', { name: '批量删除（2）' }));
    fireEvent.click(screen.getByRole('button', { name: '确认删除' }));
    expect(config.remove).toHaveBeenCalledTimes(1);
    view.unmount();
    await act(async () => resolve());
    expect(config.remove).toHaveBeenCalledTimes(1);
    expect(config.onComplete).not.toHaveBeenCalled();
  });
});
