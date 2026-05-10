import React from "react";
import { Download, Brain, Map, BarChart3, Globe, Shield } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

const features = [
  {
    title: "万能视频解析",
    description: "支持 YouTube, Bilibili, TikTok 等主流平台的 4K 视频解析与下载。",
    icon: Download,
    color: "text-blue-500",
    bg: "bg-blue-50"
  },
  {
    title: "AI 智能摘要",
    description: "利用大语言模型自动提取视频核心内容，生成结构化摘要。",
    icon: Brain,
    color: "text-purple-500",
    bg: "bg-purple-50"
  },
  {
    title: "逻辑思维导图",
    description: "一键将视频逻辑转化为思维导图，帮助您快速掌握知识脉络。",
    icon: Map,
    color: "text-emerald-500",
    bg: "bg-emerald-50"
  },
  {
    title: "深度内容分析",
    description: "多维度解析视频趋势、关键词与核心观点，助您深度消费内容。",
    icon: BarChart3,
    color: "text-orange-500",
    bg: "bg-orange-50"
  },
  {
    title: "全球多语支持",
    description: "支持跨语言视频处理，打破地域与语言的内容消费壁垒。",
    icon: Globe,
    color: "text-indigo-500",
    bg: "bg-indigo-50"
  },
  {
    title: "安全隐私保障",
    description: "企业级加密存储与匿名化处理，保障您的创作数据绝对安全。",
    icon: Shield,
    color: "text-red-500",
    bg: "bg-red-50"
  }
];

const Features: React.FC = () => {
  return (
    <section className="py-20 lg:py-32 bg-slate-50 dark:bg-slate-900/50">
      <div className="container mx-auto px-4">
        <div className="max-w-3xl mx-auto text-center mb-20 space-y-4">
          <h2 className="text-3xl lg:text-5xl font-black tracking-tight">全方位的智能工具集</h2>
          <p className="text-lg text-muted-foreground">
            我们不仅仅是下载器，更是您的私人 AI 视频知识助手。
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, i) => (
            <Card key={i} className="border-none shadow-none bg-background hover:shadow-xl hover:-translate-y-2 transition-all duration-300">
              <CardHeader>
                <div className={`w-14 h-14 rounded-2xl ${feature.bg} flex items-center justify-center mb-4`}>
                  <feature.icon className={`w-7 h-7 ${feature.color}`} />
                </div>
                <CardTitle className="text-xl font-bold">{feature.title}</CardTitle>
                <CardDescription className="text-muted-foreground text-base leading-relaxed">
                  {feature.description}
                </CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Features;
