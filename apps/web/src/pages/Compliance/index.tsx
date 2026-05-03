import { CheckCircleOutlined, StopOutlined } from '@ant-design/icons';
import { PageContainer, ProCard } from '@ant-design/pro-components';
import { Alert, List, Space, Typography } from 'antd';

const allowed = [
  '用户拥有版权的内容',
  '已获得授权的内容',
  '公共领域或开放授权内容',
  '平台明确允许保存的公开内容',
];

const denied = [
  'DRM 或访问控制规避',
  '付费墙、会员内容绕过',
  '用户平台 Cookie 托管',
  '盗版传播、批量滥采、账号共享',
];

export default function CompliancePage() {
  return (
    <PageContainer title="合规边界" subTitle="MVP 阶段保持清晰、安全、可审计">
      <div className="download-workspace">
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Alert showIcon type="info" message="当前版本只面向合法授权内容和公开允许保存的内容。" />
          <ProCard title="允许处理" bordered>
            <List
              dataSource={allowed}
              renderItem={(item) => (
                <List.Item>
                  <Space>
                    <CheckCircleOutlined className="blue-icon" />
                    <Typography.Text>{item}</Typography.Text>
                  </Space>
                </List.Item>
              )}
            />
          </ProCard>
          <ProCard title="不进入 MVP" bordered>
            <List
              dataSource={denied}
              renderItem={(item) => (
                <List.Item>
                  <Space>
                    <StopOutlined style={{ color: '#d43f3a' }} />
                    <Typography.Text>{item}</Typography.Text>
                  </Space>
                </List.Item>
              )}
            />
          </ProCard>
        </Space>
      </div>
    </PageContainer>
  );
}
