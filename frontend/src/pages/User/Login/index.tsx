import { LockOutlined, MailOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, Link, useLocation, useModel } from '@umijs/max';
import { Alert } from 'antd';
import { useEffect, useState } from 'react';

import { displayError, getCurrentUser, login } from '@/services/auth';
import { authRedirect } from '@/utils/authRedirect';

import styles from '../auth.less';

export default function LoginPage() {
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
      <section className={styles.authPanel} aria-label="邮箱登录">
        <LoginForm<API.EmailPasswordRequest>
          logo="/logo.png"
          title="帧取"
          subTitle="登录后继续解析、下载与管理你的视频"
          submitter={{ searchConfig: { submitText: '登录' } }}
          onFinish={async (values) => {
            setErrorMessage(undefined);
            try {
              const currentUser = await login(values);
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
              autoComplete: 'current-password',
              prefix: <LockOutlined />,
              size: 'large',
            }}
            placeholder="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 8, message: '密码至少需要 8 个字符' },
            ]}
          />
        </LoginForm>
        <div className={styles.formFooter}>
          还没有账号？
          <Link to={`/user/register${location.search}`}>创建账号</Link>
        </div>
      </section>
    </main>
  );
}
