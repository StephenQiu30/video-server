import React from "react";
import {
  ArrowRight,
  CheckCircle2,
  CloudDownload,
  Sparkles,
  Star,
  ShieldCheck,
  Smartphone,
  Timer,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

type FeatureItem = {
  title: string;
  description: string;
  icon: typeof CloudDownload;
};

type ProofItem = {
  role: string;
  name: string;
  quote: string;
  score: string;
};

const featureList: FeatureItem[] = [
  {
    title: "一键聚合下载",
    description: "支持主流平台公开视频，自动获取标准化任务参数，减少复杂设置。",
    icon: CloudDownload,
  },
  {
    title: "AI 助理增强",
    description: "自动提取核心摘要、关键词和知识结构，提升复用效率。",
    icon: Sparkles,
  },
  {
    title: "实时状态与重试",
    description: "从解析到下载全程可见，异常任务给出可执行的下一步建议。",
    icon: Timer,
  },
  {
    title: "安全下载边界",
    description: "保留内容来源与处理日志边界，避免 Cookie、付费墙与 DRM 规避路径。",
    icon: ShieldCheck,
  },
];

const proofList: ProofItem[] = [
  {
    role: "内容运营",
    name: "刘经理",
    quote: "页面操作明显变快，链接解析和下载反馈都很清晰，适合日常批量处理。",
    score: "4.8",
  },
  {
    role: "知识工作者",
    name: "赵同学",
    quote: "现在可以更快找到视频主旨，AI 摘要与逻辑图入口也更容易发现。",
    score: "4.9",
  },
  {
    role: "研发团队",
    name: "周工程师",
    quote: "前端信息层级清晰，CTA 与状态条路径都统一，体验更连贯。",
    score: "4.7",
  },
];

const faqItems = [
  {
    q: "支持哪些平台的公开视频？",
    a: "支持公开样本为主的平台入口，私有链接、DRM、付费墙与规避链路不在当前范围内。",
  },
  {
    q: "下载过程中卡住怎么办？",
    a: "页面会显示实时任务事件；遇到失败会给出重试按钮和具体失败提示，不会静默失败。",
  },
  {
    q: "是否有使用配额和权限控制？",
    a: "当前以本地单用户能力为主，生产化配额与权限控制会在后续上线级补齐计划中开启。",
  },
];

const LandingPage: React.FC = () => {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <section
        id="hero"
        className="relative overflow-hidden pb-16 pt-10 md:pt-14"
      >
        <div className="mx-auto flex min-h-[70vh] w-full max-w-7xl flex-col gap-10 px-4 sm:px-6 lg:px-8 pt-8">
          <p className="mx-auto inline-flex items-center rounded-full border border-sky-200/70 bg-white/70 px-3 py-1 text-xs font-medium tracking-wide text-sky-700">
            <Sparkles className="mr-2 h-3.5 w-3.5 text-sky-500" />
            全流程可视化视频工作站 · 蓝白轻量风格
          </p>
          <div className="grid items-start gap-10 lg:grid-cols-2">
            <div className="space-y-8">
              <h1 className="text-balance text-4xl font-semibold leading-tight sm:text-5xl md:text-6xl">
                视频下载与处理，
                <span className="text-sky-600"> 一站到位更轻快。</span>
              </h1>
              <p className="max-w-xl text-base leading-7 text-slate-600 md:text-lg md:leading-8">
                以 iOS 风格体验为导向的 SaaS 首页：去掉冗余装饰，保留清晰信息层级、
                智能任务流程与
                高可读性的任务动作。
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <Button
                  variant="default"
                  className="min-h-[44px] min-w-[132px] rounded-full bg-sky-500 px-7 font-semibold text-white shadow-sm shadow-sky-400/30 hover:bg-sky-600 focus-visible:ring-2 focus-visible:ring-sky-300"
                  render={(props) => (
                    <Link
                      to="/auth"
                      aria-label="立即开始使用"
                      {...props}
                    />
                  )}
                >
                  立即开始使用
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  className="min-h-[44px] min-w-[132px] rounded-full border-sky-200 text-sky-700 hover:bg-sky-50 focus-visible:ring-2 focus-visible:ring-sky-300"
                  render={(props) => (
                    <a href="#features" aria-label="跳转到功能亮点" {...props} />
                  )}
                >
                  查看功能亮点
                </Button>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                {[
                  "支持公开短链与常见长链接",
                  "任务状态实时刷新",
                  "AI 归纳与知识结构输出",
                ].map((item) => (
                  <p key={item} className="flex items-start text-sm text-slate-600">
                    <CheckCircle2 className="mr-2 mt-0.5 h-4 w-4 shrink-0 text-sky-600" />
                    <span>{item}</span>
                  </p>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className="rounded-[26px] border border-sky-100 bg-white p-5 shadow-sm">
                <div className="rounded-2xl bg-sky-50 p-5">
                  <p className="text-xs font-semibold uppercase tracking-wide text-sky-700">任务卡</p>
                  <div className="mt-4 space-y-3">
                    <div className="rounded-xl bg-white p-4 shadow-sm shadow-sky-100">
                      <p className="text-xs text-slate-500">解析中</p>
                      <p className="mt-1 text-sm font-semibold text-slate-700">https://example.video/intro</p>
                      <div className="mt-3 h-2 rounded-full bg-sky-100">
                        <div className="h-full w-3/5 rounded-full bg-sky-500" />
                      </div>
                    </div>
                    <div className="rounded-xl border border-sky-100 bg-sky-50/60 p-4">
                      <p className="text-xs text-slate-500">步骤</p>
                      <p className="mt-1 text-sm font-semibold text-slate-700">解析 &gt; 下载 &gt; 归档</p>
                    </div>
                  </div>
                </div>
                <ChevronDown className="absolute right-6 bottom-6 h-10 w-10 text-sky-200" />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="py-16 md:py-20">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-center text-3xl font-semibold tracking-tight md:text-4xl">
            核心价值
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-center text-sm text-slate-600 md:text-base">
            强调结果，不堆砌特效。把入口、反馈和任务状态按同一路径集中展示。
          </p>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {featureList.map((item) => {
              const Icon = item.icon;
              return (
                <article
                  key={item.title}
                  className="rounded-2xl border border-sky-100 bg-white p-5 transition duration-200 hover:border-sky-300 hover:shadow-sm"
                >
                  <div className="mb-4 inline-flex rounded-xl bg-sky-50 p-2">
                    <Icon className="h-5 w-5 text-sky-600" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-800">{item.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section id="proof" className="py-16 md:py-20">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid items-center gap-8 lg:grid-cols-[1.2fr_1fr]">
            <div>
              <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">社会证明 · 真实用户信任</h2>
              <p className="mt-4 max-w-lg text-slate-600">
                去掉复杂话术，保留可核验的流程和反馈。用数据与反馈说明体验质量。
              </p>
              <div className="mt-8 flex items-center gap-4">
                <Smartphone className="h-10 w-10 text-sky-500" />
                <div>
                  <p className="text-sm text-slate-500">今日任务完成</p>
                  <p className="text-3xl font-semibold text-slate-900">12,480+</p>
                </div>
              </div>
            </div>
            <div className="space-y-3">
              {proofList.map((item) => (
                <div
                  key={item.name}
                  className="rounded-2xl border border-sky-100 bg-white p-5"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <p className="font-semibold text-slate-800">{item.name} · {item.role}</p>
                    <p className="inline-flex items-center text-sm text-sky-700">
                      <Star className="mr-1 h-4 w-4 fill-sky-700" />
                      {item.score}
                    </p>
                  </div>
                  <p className="text-sm leading-6 text-slate-600">{item.quote}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="pricing" className="py-16 md:py-20">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="rounded-3xl border border-sky-100 bg-gradient-to-b from-white to-sky-50 px-6 py-10 md:px-10">
            <div className="text-center">
              <p className="text-sm font-semibold uppercase tracking-wider text-sky-700">
                选择更轻的工作方式
              </p>
              <h2 className="mt-2 text-3xl font-semibold md:text-4xl">
                目前可直接使用本地与公开样本闭环
              </h2>
            </div>
            <div className="mx-auto mt-8 grid gap-4 md:max-w-2xl md:grid-cols-3">
              <div className="rounded-2xl border border-sky-100 bg-white p-5 text-center">
                <p className="text-sm text-slate-500">试用</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">免费</p>
                <p className="mt-2 text-sm text-slate-600">任务体验 / 基础流程</p>
              </div>
              <div className="rounded-2xl border-2 border-sky-300 bg-sky-50 p-5 text-center">
                <p className="text-sm font-semibold text-sky-700">主推</p>
                <p className="mt-2 text-2xl font-semibold text-sky-900">Pro</p>
                <p className="mt-2 text-sm text-slate-600">稳定体验 / 建议团队先行</p>
              </div>
              <div className="rounded-2xl border border-sky-100 bg-white p-5 text-center">
                <p className="text-sm text-slate-500">企业</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">Soon</p>
                <p className="mt-2 text-sm text-slate-600">权限与配额在后续上线版本开放</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="faq" className="py-16 md:py-20">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid gap-5 md:grid-cols-2">
            <div>
              <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">常见问题</h2>
              <p className="mt-2 text-slate-600">先回答最关键的问题，把误区和边界讲清。</p>
            </div>
            <div className="space-y-3">
              {faqItems.map((item) => (
                <details
                  key={item.q}
                  className="rounded-xl border border-sky-100 bg-white px-4 py-3 open:border-sky-300"
                >
                  <summary className="cursor-pointer text-left font-medium text-slate-800">
                    {item.q}
                  </summary>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{item.a}</p>
                </details>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="final-cta" className="pb-20 pt-8">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="rounded-3xl border border-sky-100 bg-sky-600 px-6 py-10 text-center text-sky-50 md:px-10">
            <h3 className="text-2xl font-semibold md:text-3xl">立即试用，体验更清晰的下载与内容管理节奏。</h3>
            <p className="mx-auto mt-3 max-w-2xl text-sm text-sky-100 md:text-base">
              不堆砌装饰，聚焦动作入口。所有操作集中在同一条主线，减少反复切换。
            </p>
            <Button
              variant="outline"
              render={(props) => (
                <Link
                  to="/workbench"
                  aria-label="开始下载工作台"
                  {...props}
                />
              )}
              className="mt-6 min-h-[44px] min-w-[132px] border-white/60 bg-white/90 px-7 text-sky-700 hover:bg-white"
            >
              开启下载工作流
            </Button>
          </div>
        </div>
      </section>
    </main>
  );
};

export default LandingPage;
