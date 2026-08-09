import {
  PageContainer,
  ProForm,
  ProFormSelect,
  ProFormText,
} from '@ant-design/pro-components';
import { useModel } from '@umijs/max';
import { App } from 'antd';

import { displayError, updateCurrentUser } from '@/services/users';

type ProfileFormValues = API.UpdateProfileRequest & {
  email: string;
  role: API.UserRole;
};

export default function AccountPage() {
  const { initialState, setInitialState } = useModel('@@initialState');
  const { message } = App.useApp();
  const currentUser = initialState?.currentUser;

  if (!currentUser) {
    return null;
  }

  return (
    <PageContainer
      breadcrumb={{
        items: [{ title: '首页', href: '/' }, { title: '个人资料' }],
      }}
      title="个人资料"
    >
      <ProForm<ProfileFormValues>
        initialValues={{
          email: currentUser.email,
          role: currentUser.role,
          username: currentUser.username,
        }}
        layout="vertical"
        onFinish={async ({ username }) => {
          try {
            const updated = await updateCurrentUser({ username });
            await setInitialState({
              currentUser: updated,
              fetchCurrentUser: initialState.fetchCurrentUser,
              settings: initialState.settings,
            });
            void message.success('个人资料已更新');
            return true;
          } catch (error) {
            void message.error(displayError(error));
            return false;
          }
        }}
        submitter={{
          resetButtonProps: false,
          searchConfig: { submitText: '保存资料' },
        }}
      >
        <ProFormText
          fieldProps={{ maxLength: 32 }}
          label="用户名"
          name="username"
          rules={[
            { required: true, message: '请输入用户名' },
            { min: 2, message: '用户名至少需要 2 个字符' },
            { max: 32, message: '用户名不能超过 32 个字符' },
          ]}
          width="md"
        />
        <ProFormText disabled label="登录邮箱" name="email" width="md" />
        <ProFormSelect
          disabled
          label="账户身份"
          name="role"
          options={[
            { label: '管理员', value: 'admin' },
            { label: '普通用户', value: 'user' },
          ]}
          width="md"
        />
      </ProForm>
    </PageContainer>
  );
}
