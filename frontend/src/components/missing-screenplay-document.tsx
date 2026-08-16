import { BackLink } from '@/components/back-link';
import { Empty, EmptyDescription, EmptyHeader } from '@/components/ui/empty';

export function MissingScreenplayDocument() {
  return (
    <div className="inner-page">
      <BackLink fallbackHref="/documents" />
      <Empty className="min-h-80 items-start justify-start rounded-none border-0 p-0 pt-6 text-left sm:pt-8">
        <EmptyHeader className="items-start">
          <h1 className="text-[36px] font-medium leading-[1.02] tracking-[-0.05em] sm:text-[52px]">
            剧本文档不存在
          </h1>
          <EmptyDescription className="mt-2 text-left">
            请返回剧本文档列表，选择一个仍可访问的文档。
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    </div>
  );
}
