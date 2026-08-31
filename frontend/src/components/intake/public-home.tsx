import {
  ArrowRightIcon,
  ArrowUpRightIcon,
  CheckCircleIcon,
  GithubLogoIcon,
} from '@phosphor-icons/react/dist/ssr';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { siteConfig } from '@/lib/site';

const capabilities = [
  {
    eyebrow: '01 · MEDIA',
    title: '公开视频工作流',
    description:
      '解析你有权处理的公开链接，选择可用格式，并以异步任务跟踪下载、缩略图和最终制品。',
  },
  {
    eyebrow: '02 · SCREENPLAY',
    title: '剧本与文档处理',
    description:
      '导入获授权的剧本文档，在同一工作区完成规范化、结构分析与可追溯的处理记录。',
  },
  {
    eyebrow: '03 · ANALYSIS',
    title: '结构化 AI 视频分析',
    description:
      '围绕场景、分镜、高光和内容资产生成结构化结果，并保留任务状态与运行证据。',
  },
] as const;

const workflow = [
  ['解析', '识别公开媒体或文章中的候选视频'],
  ['选择', '确认目标与格式，避免隐式下载'],
  ['执行', '由隔离 Worker 处理下载、导入和分析'],
  ['交付', '通过授权短时入口预览或获取制品'],
] as const;

export function PublicHome() {
  return (
    <div className="flex flex-col pb-20">
      <section className="grid min-h-[calc(100svh-9rem)] items-center gap-14 border-b border-border py-16 lg:grid-cols-[minmax(0,1.2fr)_minmax(300px,0.8fr)] lg:py-24">
        <div>
          <p className="font-mono text-xs font-medium tracking-[0.2em] text-muted-foreground uppercase">
            FrameFetch · Open Source
          </p>
          <h1 className="mt-7 max-w-5xl text-balance text-[clamp(3.4rem,7vw,7.4rem)] font-medium leading-[0.88] tracking-[-0.075em]">
            开源、自托管的
            <br />
            视频工作流。
          </h1>
          <p className="mt-8 max-w-3xl text-balance text-lg leading-8 text-muted-foreground sm:text-xl">
            从获授权的公开视频与剧本文档出发，完成解析、下载、制品管理和 AI
            视频分析。数据与运行边界由你掌控。
          </p>
          <div className="mt-10 flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link href="/user/register">
                创建本地账户
                <ArrowRightIcon aria-hidden className="size-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <a
                href={siteConfig.repositoryUrl}
                rel="noreferrer"
                target="_blank"
              >
                <GithubLogoIcon aria-hidden className="size-4" />
                查看源代码
                <ArrowUpRightIcon aria-hidden className="size-4" />
              </a>
            </Button>
          </div>
        </div>

        <div className="border-l border-border pl-0 lg:pl-12">
          <p className="text-sm font-medium">一套可审计的完整链路</p>
          <ol className="mt-7 space-y-7">
            {workflow.map(([title, description], index) => (
              <li className="grid grid-cols-[2rem_1fr] gap-4" key={title}>
                <span className="font-mono text-xs text-muted-foreground">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <div>
                  <p className="font-medium">{title}</p>
                  <p className="mt-1 leading-6 text-muted-foreground">
                    {description}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section
        aria-labelledby="capabilities-title"
        className="border-b border-border py-20 lg:py-28"
        id="capabilities"
      >
        <div className="max-w-3xl">
          <p className="font-mono text-xs tracking-[0.18em] text-muted-foreground uppercase">
            Product capabilities
          </p>
          <h2
            className="mt-5 text-balance text-4xl font-medium tracking-[-0.045em] sm:text-5xl"
            id="capabilities-title"
          >
            从公开媒体到可验证制品
          </h2>
          <p className="mt-5 text-lg leading-8 text-muted-foreground">
            Web 控制面、API 与 Worker
            共享同一套权限、任务和制品模型，既适合个人本地使用，也便于团队自托管部署。
          </p>
        </div>

        <div className="mt-14 grid border-t border-border md:grid-cols-3">
          {capabilities.map((capability) => (
            <article
              className="border-b border-border py-8 md:border-b-0 md:border-r md:px-8 md:first:pl-0 md:last:border-r-0 md:last:pr-0"
              key={capability.title}
            >
              <p className="font-mono text-xs text-muted-foreground">
                {capability.eyebrow}
              </p>
              <h3 className="mt-5 text-xl font-medium tracking-[-0.025em]">
                {capability.title}
              </h3>
              <p className="mt-3 leading-7 text-muted-foreground">
                {capability.description}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section
        aria-labelledby="architecture-title"
        className="grid gap-14 border-b border-border py-20 lg:grid-cols-2 lg:gap-24 lg:py-28"
        id="architecture"
      >
        <div>
          <p className="font-mono text-xs tracking-[0.18em] text-muted-foreground uppercase">
            Built for self-hosting
          </p>
          <h2
            className="mt-5 text-balance text-4xl font-medium tracking-[-0.045em] sm:text-5xl"
            id="architecture-title"
          >
            开源，不交出数据控制权
          </h2>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-muted-foreground">
            FastAPI、Next.js、PostgreSQL、RabbitMQ、MinIO、FFmpeg 与 yt-dlp
            组成可独立部署的工作流。MIT 许可证允许你免费检查、修改和自托管。
          </p>
        </div>
        <div className="space-y-5 border-t border-border pt-7">
          {[
            '浏览器会话采用 HttpOnly Cookie；原生客户端使用可轮换令牌。',
            '下载、导入与 AI 分析通过独立队列和 Worker 执行。',
            '短时制品入口、所有者隔离与授权边界贯穿完整链路。',
            '公开视频并不等于可自由使用，请仅处理已获授权的内容。',
          ].map((item) => (
            <p className="flex gap-3 leading-7" key={item}>
              <CheckCircleIcon
                aria-hidden
                className="mt-1 size-5 shrink-0 text-success"
                weight="fill"
              />
              <span>{item}</span>
            </p>
          ))}
        </div>
      </section>

      <section className="flex flex-col items-start justify-between gap-8 py-20 sm:flex-row sm:items-end lg:py-28">
        <div>
          <p className="font-mono text-xs tracking-[0.18em] text-muted-foreground uppercase">
            Start locally
          </p>
          <h2 className="mt-5 max-w-3xl text-balance text-4xl font-medium tracking-[-0.045em] sm:text-5xl">
            在自己的基础设施上运行 FrameFetch
          </h2>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-muted-foreground">
            从仓库的 Quick
            Start、架构文档和安全边界开始，按需启用媒体解析、剧本工作流与 AI
            服务。
          </p>
        </div>
        <Button asChild size="lg" variant="outline">
          <a href={`${siteConfig.repositoryUrl}/blob/main/README.md#快速开始`}>
            阅读部署说明
            <ArrowUpRightIcon aria-hidden className="size-4" />
          </a>
        </Button>
      </section>
    </div>
  );
}
