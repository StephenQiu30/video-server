import {
  CheckCircleOutlined,
  CloudDownloadOutlined,
  DatabaseOutlined,
  LinkOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { history } from '@@/core/history';
import { Button, Space, Typography } from 'antd';

const workflow = [
  { title: '解析公开视频', desc: '先读取标题、时长和可用格式，确认链接是否适合进入下载任务。' },
  { title: '后台任务处理', desc: '下载、合并和校验交给 Worker，页面只关注状态和失败原因。' },
  { title: '私有存储交付', desc: '文件进入私有 bucket，通过短期预签名链接交付下载。' },
];

const boundaries = ['不托管平台 Cookie', '不绕过 DRM / 付费墙', '不做平台专用解析', '只处理授权或公开允许保存的内容'];

export default function HomePage() {
  return (
    <main className="home-page">
      <section className="home-hero">
        <div className="home-hero-copy">
          <Typography.Text className="home-eyebrow">M1 MVP / Local Single-user</Typography.Text>
          <Typography.Title level={1}>Stephen Video</Typography.Title>
          <Typography.Paragraph className="home-lead">
            面向本地自用的合规视频下载与内容整理平台。当前阶段优先跑通“解析、创建任务、后台下载、私有存储、短期下载链接”的核心链路。
          </Typography.Paragraph>
          <Space size={12} wrap>
            <Button type="primary" size="large" icon={<LinkOutlined />} onClick={() => history.push('/workspace')}>
              进入下载工作台
            </Button>
            <Button size="large" icon={<CloudDownloadOutlined />} onClick={() => history.push('/tasks')}>
              查看任务历史
            </Button>
          </Space>
        </div>

        <div className="home-console" aria-label="MVP workflow preview">
          <div className="console-bar">
            <span />
            <span />
            <span />
          </div>
          <div className="console-body">
            <div className="console-input">
              <LinkOutlined />
              <span>https://example.com/public-video</span>
              <strong>Parse</strong>
            </div>
            <div className="console-flow">
              <div>
                <CheckCircleOutlined />
                <span>解析完成</span>
              </div>
              <div>
                <CloudDownloadOutlined />
                <span>任务排队</span>
              </div>
              <div>
                <DatabaseOutlined />
                <span>私有存储</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="home-section">
        <div className="home-section-heading">
          <Typography.Text className="home-eyebrow">Core Flow</Typography.Text>
          <Typography.Title level={2}>先把可验证的业务闭环跑稳</Typography.Title>
        </div>
        <div className="home-flow-grid">
          {workflow.map((item, index) => (
            <article className="home-flow-card" key={item.title}>
              <span className="flow-index">{String(index + 1).padStart(2, '0')}</span>
              <Typography.Title level={4}>{item.title}</Typography.Title>
              <Typography.Paragraph>{item.desc}</Typography.Paragraph>
            </article>
          ))}
        </div>
      </section>

      <section className="home-boundary">
        <div>
          <SafetyCertificateOutlined />
          <Typography.Title level={3}>MVP 合规边界</Typography.Title>
        </div>
        <div className="boundary-list">
          {boundaries.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      </section>
    </main>
  );
}
