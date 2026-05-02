import { LockOutlined, MailOutlined, UserOutlined } from '@ant-design/icons';
import { LoginFormPage, ProFormText } from '@ant-design/pro-components';
import { history } from '@@/core/history';
import { useModel } from '@@/plugin-model';
import { Alert, Tabs, Typography, message } from 'antd';
import { useState } from 'react';
import { login, register, setToken } from '../../services/api';

export default function LoginPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const { setInitialState } = useModel('@@initialState');

  return (
    <div className="login-page">
      <div className="login-panel">
        <LoginFormPage
          title="Stephen Video"
          subTitle="合规可自部署的视频下载工作台"
          submitter={{ searchConfig: { submitText: mode === 'login' ? '登录' : '创建账号' } }}
          onFinish={async (values) => {
            const payload = values as API.AuthPayload;
            const result =
              mode === 'login'
                ? await login({ email: payload.email, password: payload.password })
                : await register(payload);
            setToken(result.access_token);
            await setInitialState((state: any) => ({ ...state, currentUser: result.user }));
            message.success(mode === 'login' ? '登录成功' : '账号已创建');
            history.push('/workspace');
          }}
        >
          <Tabs
            centered
            activeKey={mode}
            onChange={(key) => setMode(key as 'login' | 'register')}
            items={[
              { key: 'login', label: '登录' },
              { key: 'register', label: '注册' },
            ]}
          />
          <ProFormText
            name="email"
            fieldProps={{ size: 'large', prefix: <MailOutlined /> }}
            placeholder="邮箱"
            rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '邮箱格式不正确' }]}
          />
          {mode === 'register' ? (
            <ProFormText
              name="display_name"
              fieldProps={{ size: 'large', prefix: <UserOutlined /> }}
              placeholder="显示名称"
            />
          ) : null}
          <ProFormText.Password
            name="password"
            fieldProps={{ size: 'large', prefix: <LockOutlined /> }}
            placeholder="密码"
            rules={[{ required: true, message: '请输入密码' }, { min: mode === 'register' ? 8 : 1 }]}
          />
          <Alert
            showIcon
            type="info"
            message="仅处理你拥有版权、已获授权或公开允许保存的内容。"
            style={{ marginBlockStart: 8 }}
          />
        </LoginFormPage>
      </div>
      <div className="login-visual">
        <div className="login-visual-grid">
          <div className="signal-tile">
            <Typography.Text type="secondary">服务状态</Typography.Text>
            <Typography.Title level={2}>API / Worker / Storage</Typography.Title>
          </div>
          <div className="signal-tile">
            <Typography.Text type="secondary">任务模型</Typography.Text>
            <Typography.Title level={2}>Parse {'->'} Queue {'->'} Download</Typography.Title>
          </div>
          <div className="workflow-tile">
            <Typography.Text type="secondary">MVP 边界</Typography.Text>
            <Typography.Title level={3}>公开内容解析、后台任务、私有存储、短期下载链接</Typography.Title>
          </div>
        </div>
      </div>
    </div>
  );
}
