import {
  type ActionType,
  ModalForm,
  PageContainer,
  type ProColumns,
  ProFormSelect,
  ProFormSwitch,
  ProTable,
} from '@ant-design/pro-components';
import { useModel } from '@umijs/max';
import { App, Button, Tag, Tooltip } from 'antd';
import { useMemo, useRef, useState } from 'react';

import { displayError, listUsers, updateUserAccess } from '@/services/users';

type UserSearchParams = {
  is_active?: 'true' | 'false';
  role?: API.UserRole;
  search?: string;
};

export default function AdminUsersPage() {
  const { initialState } = useModel('@@initialState');
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>(undefined);
  const [editing, setEditing] = useState<API.ManagedUserResponse>();
  const currentUserId = initialState?.currentUser?.id;

  const columns = useMemo<ProColumns<API.ManagedUserResponse>[]>(
    () => [
      {
        title: '用户',
        dataIndex: 'search',
        hideInTable: true,
        order: 3,
        fieldProps: { allowClear: true, placeholder: '搜索用户名或邮箱' },
      },
      { title: '用户名', dataIndex: 'username', search: false },
      { title: '邮箱', dataIndex: 'email', search: false },
      {
        title: '身份',
        dataIndex: 'role',
        valueType: 'select',
        valueEnum: roleValueEnum,
        order: 2,
        width: 120,
        render: (_, user) => (
          <Tag color={user.role === 'admin' ? 'blue' : 'default'}>
            {roleValueEnum[user.role].text}
          </Tag>
        ),
      },
      {
        title: '状态',
        dataIndex: 'is_active',
        valueType: 'select',
        valueEnum: activeValueEnum,
        order: 1,
        width: 120,
        render: (_, user) => (
          <Tag color={user.is_active ? 'success' : 'default'}>
            {user.is_active ? '已启用' : '已停用'}
          </Tag>
        ),
      },
      {
        title: '注册时间',
        dataIndex: 'created_at',
        valueType: 'dateTime',
        search: false,
        width: 190,
      },
      {
        title: '操作',
        valueType: 'option',
        width: 100,
        render: (_, user) => {
          const isSelf = user.id === currentUserId;
          return (
            <Tooltip title={isSelf ? '不能修改自己的管理员身份' : undefined}>
              <Button
                disabled={isSelf}
                onClick={() => setEditing(user)}
                type="link"
              >
                管理
              </Button>
            </Tooltip>
          );
        },
      },
    ],
    [currentUserId],
  );

  return (
    <PageContainer
      breadcrumb={{
        items: [{ title: '首页', href: '/' }, { title: '用户管理' }],
      }}
      title="用户管理"
    >
      <ProTable<API.ManagedUserResponse, UserSearchParams>
        actionRef={actionRef}
        cardBordered={false}
        columns={columns}
        headerTitle="用户列表"
        options={{ density: false, fullScreen: false, setting: false }}
        pagination={{ defaultPageSize: 20, showSizeChanger: false }}
        request={async ({ current = 1, pageSize = 20, ...filters }) => {
          const result = await listUsers({
            page: current,
            page_size: pageSize,
            search: filters.search?.trim() || undefined,
            role: filters.role,
            is_active:
              filters.is_active === undefined
                ? undefined
                : filters.is_active === 'true',
          });
          return { data: result.items, success: true, total: result.total };
        }}
        rowKey="id"
        search={{ collapseRender: false, labelWidth: 'auto' }}
        scroll={{ x: 1000 }}
      />

      <ModalForm<API.UpdateUserAccessRequest>
        initialValues={{ role: editing?.role, is_active: editing?.is_active }}
        key={editing?.id}
        modalProps={{ destroyOnHidden: true }}
        onFinish={async (values) => {
          if (!editing) return false;
          try {
            await updateUserAccess(editing.id, values);
            void message.success('用户权限已更新');
            setEditing(undefined);
            await actionRef.current?.reload();
            return true;
          } catch (error) {
            void message.error(displayError(error));
            return false;
          }
        }}
        onOpenChange={(open) => {
          if (!open) setEditing(undefined);
        }}
        open={Boolean(editing)}
        submitter={{ searchConfig: { submitText: '保存' } }}
        title={`管理用户${editing ? `：${editing.username}` : ''}`}
      >
        <ProFormSelect
          label="账户身份"
          name="role"
          options={[
            { label: '管理员', value: 'admin' },
            { label: '普通用户', value: 'user' },
          ]}
          rules={[{ required: true }]}
        />
        <ProFormSwitch label="启用账号" name="is_active" />
      </ModalForm>
    </PageContainer>
  );
}

const roleValueEnum = {
  admin: { text: '管理员' },
  user: { text: '普通用户' },
};

const activeValueEnum = {
  true: { text: '已启用' },
  false: { text: '已停用' },
};
