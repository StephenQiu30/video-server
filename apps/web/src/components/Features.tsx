import React, { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Zap, Shield, Cpu, Layout } from "lucide-react";

gsap.registerPlugin(ScrollTrigger);

const features = [
  {
    name: "极速解析引擎",
    description: "我们的分布式引擎可在毫秒内提取高质量视频链接。",
    icon: Zap,
    color: "text-yellow-500",
  },
  {
    name: "4K 分辨率支持",
    description: "手动选择您喜欢的质量，从移动设备适配到清晰的 4K。",
    icon: Layout,
    color: "text-blue-500",
  },
  {
    name: "AI 智能分析 (测试版)",
    description: "为任何视频获取自动总结、思维导图和情感分析。",
    icon: Cpu,
    color: "text-purple-500",
  },
  {
    name: "企业级安全",
    description: "您的下载和数据受到银行级加密保护。",
    icon: Shield,
    color: "text-green-500",
  },
];

const Features: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const cards = gsap.utils.toArray(".feature-card");
    
    gsap.fromTo(
      cards,
      { y: 60, opacity: 0 },
      {
        y: 0,
        opacity: 1,
        duration: 0.8,
        stagger: 0.2,
        scrollTrigger: {
          trigger: containerRef.current,
          start: "top 80%",
        },
      }
    );
  }, []);

  return (
    <div className="bg-background py-24 sm:py-32" id="features" ref={containerRef}>
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl lg:text-center">
          <h2 className="text-base font-semibold leading-7 text-primary">您所需的一切</h2>
          <p className="mt-2 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            专为创作者和开发者设计
          </p>
          <p className="mt-6 text-lg leading-8 text-muted-foreground">
            一套全面的工具集，以无与伦比的速度和精度管理您的视频工作区。
          </p>
        </div>
        <div className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none">
          <dl className="grid max-w-xl grid-cols-1 gap-x-8 gap-y-16 lg:max-w-none lg:grid-cols-4">
            {features.map((feature) => (
              <div key={feature.name} className="feature-card flex flex-col items-start p-8 rounded-2xl bg-card border border-border hover:shadow-xl transition-shadow group">
                <div className={`rounded-lg bg-background p-3 ring-1 ring-border group-hover:ring-primary transition-all`}>
                  <feature.icon className={`h-6 w-6 ${feature.color}`} aria-hidden="true" />
                </div>
                <dt className="mt-4 font-semibold text-foreground">{feature.name}</dt>
                <dd className="mt-2 leading-7 text-muted-foreground">{feature.description}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </div>
  );
};

export default Features;
