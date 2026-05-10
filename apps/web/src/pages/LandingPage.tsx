import React from "react";
import Hero from "../components/Hero";
import Features from "../components/Features";

const LandingPage: React.FC = () => {
  return (
    <main className="min-h-screen">
      <Hero />
      <Features />
      
      {/* Visual divider */}
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="h-px bg-border" />
      </div>
      
      {/* Footer-like CTA */}
      <section className="py-24 text-center">
        <h3 className="text-2xl font-bold">准备好彻底改变您的工作流程了吗？</h3>
        <p className="text-muted-foreground mt-4 max-w-md mx-auto">
          加入成千上万信任我们进行视频下载和处理的用户行列。
        </p>
        <button className="mt-8 rounded-full bg-primary px-8 py-3 font-semibold text-primary-foreground hover:bg-primary/90 transition-all">
          免费开始使用
        </button>
      </section>
    </main>
  );
};

export default LandingPage;
