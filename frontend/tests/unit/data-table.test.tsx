import { render, screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';
import { DataTable } from '@/components/layout/data-table';

type Row = { id: string; name: string; state: string };
const rows: Row[] = [{ id: 'a', name: '第一条', state: '已完成' }];
const columns = [
  { id: 'name', header: '内容', cell: (item: Row) => item.name },
  { id: 'state', header: '状态', cell: (item: Row) => item.state },
];

it('keeps column options in the header and reserves no empty toolbar row', () => {
  const { container } = render(
    <DataTable
      data={rows}
      columns={columns}
      caption="记录"
      getRowId={(item) => item.id}
    />,
  );
  const header = screen.getAllByRole('columnheader').at(-1);
  expect(header).toBeDefined();
  expect(
    within(header as HTMLElement).getByRole('button', { name: '显示列' }),
  ).toBeInTheDocument();
  const toolbar = container.querySelector('[data-slot="table-toolbar"]');
  expect(toolbar).toBeEmptyDOMElement();
  expect(toolbar).toHaveClass('empty:hidden');
});

it('renders a supplied toolbar in its own row', () => {
  render(
    <DataTable
      data={rows}
      columns={columns}
      caption="记录"
      getRowId={(item) => item.id}
      toolbar={<span>已选 1 项</span>}
    />,
  );
  expect(screen.getByText('已选 1 项')).toBeInTheDocument();
});
