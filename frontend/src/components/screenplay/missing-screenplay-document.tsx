import { PageEmptyNotice } from '@/components/layout/page-empty-notice';
import { PageNavigation } from '@/components/layout/page-navigation';

export function MissingScreenplayDocument() {
  return (
    <div className="inner-page">
      <PageNavigation fallbackHref="/documents" />
      <PageEmptyNotice
        description="请返回剧本文档列表，选择一个仍可访问的文档。"
        title="剧本文档不存在"
        titleAs="h1"
      />
    </div>
  );
}
