import { BackLink } from '@/components/layout/back-link';
import { PageEmptyNotice } from '@/components/layout/page-empty-notice';

export default function MissingDownload() {
  return (
    <div className="inner-page">
      <BackLink className="mb-4" fallbackHref="/history" />
      <PageEmptyNotice
        description="请从下载记录重新打开任务，或返回首页创建新的下载。"
        title="下载任务不存在"
        titleAs="h1"
        titleClassName="text-[clamp(2.5rem,4vw,3rem)] font-semibold leading-none tracking-[-0.05em]"
      />
    </div>
  );
}
