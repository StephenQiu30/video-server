import { Button, Result } from 'antd';
import { useNavigate } from 'react-router-dom';

export default function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <Result
      status="404"
      title="页面不存在"
      subTitle="请检查地址，或返回下载页面。"
      extra={<Button onClick={() => navigate('/download')}>返回下载</Button>}
    />
  );
}
