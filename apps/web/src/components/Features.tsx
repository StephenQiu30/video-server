import React, { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Zap, Shield, Cpu, Layout, Globe, Activity } from "lucide-react";

gsap.registerPlugin(ScrollTrigger);

const features = [
  {
    name: "极速解析引擎",
    description: "我们的分布式引擎可在毫秒内提取高质量视频链接，支持全球主流平台。",
    icon: Zap,
    color: "from-yellow-400 to-orange-500",
  },
  {
    name: "4K 极致画质",
    description: "手动选择您喜欢的质量，从移动设备适配到清晰无损的 4K 原始分辨率。",
    icon: Layout,
    color: "from-blue-400 to-indigo-500",
  },
  {
    name: "AI 智能洞察",
    description: "为任何视频获取自动总结、思维导图和情感分析，深度挖掘视频价值。",
    icon: Cpu,
    color: "from-purple-400 to-pink-500",
  },
  {
    name: "企业级安全",
    description: "您的下载和数据受到银行级加密保护，严格遵守隐私保护协议。",
    icon: Shield,
    color: "from-green-400 to-emerald-500",
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
    <div className="py-24 sm:py-32 relative overflow-hidden" id="features" ref={containerRef}>
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl lg:text-center">
          <div className="flex items-center justify-center gap-2 text-primary font-bold tracking-widest uppercase text-xs mb-4">
             <Activity className="w-4 h-4" />
             核心能力
          </div>
          <h2 className="text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl">
            专为极致创作而生
          </h2>
          <p className="mt-6 text-xl leading-relaxed text-muted-foreground">
            一套全面的智能工具集，以无与伦比的速度和精度管理您的视频工作流。
          </p>
        </div>
        
        <div className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-4">
            {features.map((feature) => (
              <div 
                key={feature.name} 
                className="feature-card group relative p-10 rounded-3xl bg-card border border-border hover:border-primary/50 transition-all duration-500 hover:shadow-[0_20px_50px_rgba(0,0,0,0.1)] dark:hover:shadow-[0_20px_50px_rgba(0,0,0,0.3)] overflow-hidden"
              >
                <div className={`absolute top-0 left-0 w-2 h-full bg-gradient-to-b ${feature.color} opacity-0 group-hover:opacity-100 transition-opacity`} />
                
                <div className={`inline-flex rounded-2xl p-4 bg-gradient-to-br ${feature.color} text-white shadow-lg mb-6 group-hover:scale-110 transition-transform duration-500`}>
                  <feature.icon className="h-6 w-6" aria-hidden="true" />
                </div>
                
                <h3 className="text-xl font-bold text-foreground mb-3">{feature.name}</h3>
                <p className="text-muted-foreground leading-relaxed text-sm">
                  {feature.description}
                </p>
                
                <div className="mt-8 flex items-center text-primary font-bold text-xs group-hover:gap-2 transition-all cursor-pointer">
                  了解更多
                  <Globe className="w-3 h-3 opacity-0 group-hover:opacity-100" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Features;
