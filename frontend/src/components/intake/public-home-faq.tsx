import { publicQuestions } from '@/components/intake/public-home-content';
import { EditorialIntro } from '@/components/layout/editorial-intro';

export function PublicHomeFaq() {
  return (
    <section
      aria-labelledby="questions-title"
      className="scroll-mt-24 py-20 lg:py-28"
      data-slot="borderless-section"
      id="questions"
    >
      <EditorialIntro
        as="h2"
        eyebrow="常见问题"
        description="了解输入、分析结果、运行成本与移动端支持范围。"
        title="开始使用前，先了解这些"
        titleId="questions-title"
      />
      <div className="mt-12 grid gap-x-20 gap-y-10 md:grid-cols-2">
        {publicQuestions.map(({ id, question, answer }) => (
          <section
            className="scroll-mt-24"
            id={id}
            key={id}
            aria-labelledby={`${id}-title`}
          >
            <h3 className="text-lg font-medium" id={`${id}-title`}>
              {question}
            </h3>
            <p className="mt-3 text-sm leading-7 text-muted-foreground">
              {answer}
            </p>
          </section>
        ))}
      </div>
    </section>
  );
}
