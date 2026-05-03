import {
  CloudDownloadOutlined,
  DatabaseOutlined,
  LinkOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { history } from '@@/core/history';
import { PageContainer, ProCard } from '@ant-design/pro-components';
import { Alert, Button, Descriptions, Result, Space, Steps, Typography } from 'antd';

const workflow = [
  { title: '解析链接', description: '读取公开视频标题、时长和可用格式', icon: <LinkOutlined /> },
  { title: '创建任务', description: '交给 RQ Worker 后台下载和校验', icon: <CloudDownloadOutlined /> },
  { title: '私有交付', description: '写入私有对象存储并生成短期下载 URL', icon: <DatabaseOutlined /> },
];

export default function HomePage() {
  return (
    <PageContainer title="Stephen Video" subTitle="本地单用户 MVP 下载工作台">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <ProCard bordered>
          <Result
            icon={<CloudDownloadOutlined />}
            title="合规视频下载与内容整理"
            subTitle="当前阶段只面向本地自用，优先跑通解析、任务下载、私有存储和短期下载链接。"
            extra={[
              <Button key="workspace" type="primary" icon={<LinkOutlined />} onClick={() => history.push('/workspace')}>
                进入下载工作台
              </Button>,
              <Button key="tasks" onClick={() => history.push('/tasks')}>
                查看任务历史
              </Button>,
            ]}
          />
        </ProCard>

        <ProCard title="核心流程" bordered>
          <Steps items={workflow} />
        </ProCard>

        <ProCard title="M1 边界" bordered>
          <Descriptions column={{ xs: 1, md: 2 }} bordered size="small">
            <Descriptions.Item label="运行模式">本地单用户，无登录认证</Descriptions.Item>
            <Descriptions.Item label="文件交付">后端短期签名代理下载</Descriptions.Item>
            <Descriptions.Item label="任务机制">队列、状态、事件、失败重试</Descriptions.Item>
            <Descriptions.Item label="存储方式">私有 MinIO / S3 bucket</Descriptions.Item>
          </Descriptions>
        </ProCard>

        <Alert
          type="info"
          showIcon
          icon={<SafetyCertificateOutlined />}
          message={<Typography.Text>仅处理你拥有版权、已获授权、公共领域、开放授权或平台明确允许保存的内容。</Typography.Text>}
        />
      </Space>
    </PageContainer>
  );
}
