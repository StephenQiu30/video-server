import React, { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ArrowRight, Play, Sparkles } from "lucide-react";

const Hero: React.FC = () => {
  const heroRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const subRef = useRef<HTMLParagraphElement>(null);
  const btnRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
    
    tl.fromTo(
      titleRef.current,
      { y: 50, opacity: 0 },
      { y: 0, opacity: 1, duration: 1, delay: 0.2 }
    )
    .fromTo(
      subRef.current,
      { y: 30, opacity: 0 },
      { y: 0, opacity: 1, duration: 1 },
      "-=0.6"
    )
    .fromTo(
      btnRef.current,
      { scale: 0.9, opacity: 0 },
      { scale: 1, opacity: 1, duration: 0.8 },
      "-=0.6"
    );
  }, []);

  return (
    <div ref={heroRef} className="relative isolate overflow-hidden bg-background pt-24 pb-16 sm:pt-32 sm:pb-24">
      {/* Dynamic Background */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-[120px] animate-pulse" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[120px] animate-pulse delay-700" />
      </div>

      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-4xl text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-bold mb-8 animate-in fade-in slide-in-from-bottom-2 duration-1000">
            <Sparkles className="w-3 h-3" />
            <span>AI 驱动的下一代下载器</span>
          </div>
          
          <h1
            ref={titleRef}
            className="text-5xl font-extrabold tracking-tight sm:text-7xl lg:text-8xl mb-8 leading-[1.1]"
          >
            开启前所未有的 <br />
            <span className="text-gradient">视频创作体验</span>
          </h1>
          
          <p ref={subRef} className="mt-6 text-xl leading-relaxed text-muted-foreground max-w-2xl mx-auto">
            终极智能平台，提供极速视频解析与 4K 高端下载。 
            融合 AI 智能分析与思维导图，让您的媒体库管理步入智能时代。
          </p>

          <div ref={btnRef} className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-6">
            <button className="w-full sm:w-auto rounded-2xl bg-primary px-10 py-5 text-base font-bold text-primary-foreground shadow-2xl shadow-primary/40 hover:bg-primary/90 hover:-translate-y-1 active:scale-95 transition-all flex items-center justify-center gap-3 group">
              立即免费开始
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
            <button className="w-full sm:w-auto rounded-2xl px-10 py-5 text-base font-bold border border-border bg-background/50 backdrop-blur-sm hover:bg-muted transition-all flex items-center justify-center gap-3">
              观看演示
              <Play className="w-5 h-5 fill-current" />
            </button>
          </div>
        </div>
      </div>
      
      {/* Decorative lines or shapes could go here */}
    </div>
  );
};

export default Hero;
