import { PageEmptyNotice } from '@/components/layout/page-empty-notice';
import { PageNavigation } from '@/components/layout/page-navigation';

export default function MissingDownload() {
  return (
    <div className="inner-page">
      <PageNavigation fallbackHref="/history" />
      <PageEmptyNotice
        description="请从下载记录重新打开任务，或返回首页创建新的下载。"
        title="下载任务不存在"
        titleAs="h1"
      />
    </div>
  );
}
