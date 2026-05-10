import React from "react";
import { Link } from "react-router-dom";
import { Video, ArrowRight, Play, Shield, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";

const Hero: React.FC = () => {
  return (
    <section className="relative py-20 lg:py-32 overflow-hidden bg-background">
      <div className="container mx-auto px-4 relative z-10">
        <div className="max-w-4xl mx-auto text-center space-y-10">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-secondary text-secondary-foreground text-sm font-medium animate-in fade-in slide-in-from-top-4 duration-500">
            <Zap className="w-4 h-4 text-primary fill-current" />
            <span>智能视频下载与 AI 处理套件</span>
          </div>
          
          <h1 className="text-5xl lg:text-7xl font-black tracking-tight leading-[1.1] animate-in fade-in slide-in-from-top-6 duration-700 delay-100">
            重塑您的视频内容 <br /> 
            <span className="text-primary">消费与分析体验</span>
          </h1>
          
          <p className="text-xl text-muted-foreground leading-relaxed max-w-2xl mx-auto animate-in fade-in slide-in-from-top-8 duration-700 delay-200">
            利用最先进的 AI 智能，一键从主流平台下载、总结并生成视频内容的逻辑思维导图。
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4 animate-in fade-in slide-in-from-top-10 duration-700 delay-300">
            <Button 
              size="lg" 
              className="h-14 px-10 text-lg rounded-2xl shadow-lg shadow-primary/20 flex items-center gap-2"
              render={(props) => <Link to="/auth" {...props} />}
            >
              立即开始使用 <ArrowRight className="w-5 h-5" />
            </Button>
            <Button size="lg" variant="outline" className="h-14 px-10 text-lg rounded-2xl">
              <Play className="w-5 h-5 mr-2" /> 观看演示
            </Button>
          </div>

          <div className="pt-16 flex flex-wrap justify-center items-center gap-10 opacity-50 animate-in fade-in duration-1000 delay-500">
             <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest">
                <Shield className="w-4 h-4" /> 隐私保护
             </div>
             <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest">
                <Zap className="w-4 h-4" /> 极速下载
             </div>
             <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest">
                <Video className="w-4 h-4" /> 多平台支持
             </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
