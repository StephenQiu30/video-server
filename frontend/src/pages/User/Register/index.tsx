import { LockOutlined, MailOutlined, UserOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, Link, useLocation, useModel } from '@umijs/max';
import { Alert } from 'antd';
import { useEffect, useState } from 'react';

import { displayError, getCurrentUser, register } from '@/services/auth';
import { authRedirect } from '@/utils/authRedirect';

import styles from '../auth.less';

type RegisterValues = API.RegisterRequest & {
  confirmPassword: string;
};

export default function RegisterPage() {
  const { initialState, setInitialState } = useModel('@@initialState');
  const location = useLocation();
  const [errorMessage, setErrorMessage] = useState<string>();
  const redirect = authRedirect(location.search);

  useEffect(() => {
    if (initialState?.currentUser) {
      history.replace(redirect);
    }
  }, [initialState?.currentUser, redirect]);

  return (
    <main className={styles.authPage}>
      <section className={styles.authPanel} aria-label="邮箱注册">
        <LoginForm<RegisterValues>
          logo="/logo.png"
          title="创建账号"
          subTitle="使用邮箱注册，登录状态会在受信任设备上自动保持"
          submitter={{ searchConfig: { submitText: '注册并登录' } }}
          onFinish={async ({ username, email, password }) => {
            setErrorMessage(undefined);
            try {
              const currentUser = await register({ username, email, password });
              await setInitialState({
                currentUser,
                fetchCurrentUser: getCurrentUser,
                settings: initialState?.settings,
              });
              history.replace(redirect);
              return true;
            } catch (error) {
              setErrorMessage(displayError(error));
              return false;
            }
          }}
        >
          {errorMessage ? (
            <Alert
              className={styles.formError}
              message={errorMessage}
              type="error"
              showIcon
            />
          ) : null}
          <ProFormText
            name="username"
            fieldProps={{
              autoComplete: 'username',
              prefix: <UserOutlined />,
              size: 'large',
            }}
            placeholder="用户名"
            rules={[
              { required: true, message: '请设置用户名' },
              { min: 2, message: '用户名至少需要 2 个字符' },
              { max: 32, message: '用户名不能超过 32 个字符' },
            ]}
          />
          <ProFormText
            name="email"
            fieldProps={{
              autoComplete: 'email',
              prefix: <MailOutlined />,
              size: 'large',
            }}
            placeholder="邮箱地址"
            rules={[
              { required: true, message: '请输入邮箱地址' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          />
          <ProFormText.Password
            name="password"
            fieldProps={{
              autoComplete: 'new-password',
              prefix: <LockOutlined />,
              size: 'large',
            }}
            placeholder="设置密码（至少 8 个字符）"
            rules={[
              { required: true, message: '请设置密码' },
              { min: 8, message: '密码至少需要 8 个字符' },
              { max: 128, message: '密码不能超过 128 个字符' },
            ]}
          />
          <ProFormText.Password
            name="confirmPassword"
            dependencies={['password']}
            fieldProps={{
              autoComplete: 'new-password',
              prefix: <LockOutlined />,
              size: 'large',
            }}
            placeholder="确认密码"
            rules={[
              { required: true, message: '请再次输入密码' },
              ({ getFieldValue }) => ({
                validator: async (_, value) => {
                  if (!value || getFieldValue('password') === value) {
                    return;
                  }
                  throw new Error('两次输入的密码不一致');
                },
              }),
            ]}
          />
        </LoginForm>
        <div className={styles.formFooter}>
          已有账号？
          <Link to={`/user/login${location.search}`}>返回登录</Link>
        </div>
      </section>
    </main>
  );
}
