import { BackLink } from '@/components/layout/back-link';
import { PageEmptyNotice } from '@/components/layout/page-empty-notice';

export function MissingScreenplayDocument() {
  return (
    <div className="inner-page">
      <BackLink fallbackHref="/documents" />
      <PageEmptyNotice
        description="请返回剧本文档列表，选择一个仍可访问的文档。"
        title="剧本文档不存在"
        titleAs="h1"
        titleClassName="text-[36px] font-medium leading-[1.02] tracking-[-0.05em] sm:text-[52px]"
      />
    </div>
  );
}
