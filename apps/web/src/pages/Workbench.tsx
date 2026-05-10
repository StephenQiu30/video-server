import React, { useState } from "react";
import { Search, List, BarChart3, Settings, Brain, MessageSquare, Map, CheckCircle2, Clock, Sparkles, FileText, ChevronRight } from "lucide-react";
import { cn } from "../lib/utils";
import ReactMarkdown from "react-markdown";
import Mermaid from "../components/Mermaid";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

interface VideoFormat {
  format_id: string;
  quality_label?: string;
  resolution?: string;
  label: string;
  kind?: string;
}

interface ParseResult {
  url: string;
  title: string;
  cover_url?: string;
  source_site?: string;
  duration_seconds: number;
  formats: VideoFormat[];
}

interface Task {
  id: string;
  title?: string;
  state: string;
  progress: number;
  ai_summary?: string;
  ai_mindmap?: string;
}

const Workbench: React.FC = () => {
  const [url, setUrl] = useState("");
  const [step, setStep] = useState(1); // 1: Input, 2: Selection
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isAIModalOpen, setIsAIModalOpen] = useState(false);
  
  const queryClient = useQueryClient();

  // Mutation for parsing URL
  const parseMutation = useMutation({
    mutationFn: async (url: string) => {
      const response = await api.post("/parse", { url });
      return response.data;
    },
    onSuccess: (data) => {
      setParseResult(data);
      setStep(2);
    },
  });

  // Query for fetching tasks
  const { data: tasksData, isLoading: isLoadingTasks } = useQuery({
    queryKey: ["tasks"],
    queryFn: async () => {
      const response = await api.get("/tasks");
      return response.data;
    },
    refetchInterval: 3000, // Poll every 3s
  });

  const handleAnalyze = () => {
    parseMutation.mutate(url);
  };

  // Mutation for creating task
  const createTaskMutation = useMutation({
    mutationFn: async (formatId: string) => {
      if (!parseResult) throw new Error("No parse result");
      const response = await api.post("/tasks", {
        url: parseResult.url,
        format_id: formatId,
        title: parseResult.title,
        cover_url: parseResult.cover_url,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      setStep(1);
      setUrl("");
    },
  });

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 md:p-8 lg:p-12">
      <div className="max-w-7xl mx-auto space-y-12">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 animate-in fade-in slide-in-from-top-4 duration-700">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight text-gradient">智能控制中心</h1>
            <p className="text-muted-foreground mt-2 text-lg">高效驱动您的视频处理全生命周期。</p>
          </div>
          <div className="flex items-center gap-4">
            <button className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-border bg-card/50 backdrop-blur-md hover:bg-muted transition-all font-semibold">
              <Settings className="w-5 h-5" /> 配置
            </button>
            <button className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-xl shadow-primary/20 font-bold">
              升级专业版
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          {/* Main Control Panel */}
          <div className="lg:col-span-8 space-y-10">
            <div className="p-10 rounded-[2rem] border border-border glass-card relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full blur-3xl group-hover:bg-primary/10 transition-colors" />
              
              <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
                <Search className="w-6 h-6 text-primary" /> 开始新创作
              </h2>
              <div className="space-y-6">
                <div className="relative group">
                  <input
                    type="text"
                    placeholder="粘贴视频链接 (YouTube, Bilibili, TikTok...)"
                    className="w-full px-6 py-5 rounded-2xl border border-border bg-background/50 focus:ring-4 focus:ring-primary/10 focus:border-primary outline-none transition-all pr-36 text-lg shadow-inner"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                  />
                  <button 
                    onClick={handleAnalyze}
                    disabled={!url || parseMutation.isPending}
                    className="absolute right-2.5 top-2.5 bottom-2.5 px-8 rounded-xl bg-primary text-primary-foreground font-bold disabled:opacity-50 hover:shadow-lg transition-all"
                  >
                    {parseMutation.isPending ? "分析中..." : "解析"}
                  </button>
                </div>

                {step === 2 && parseResult && (
                  <div className="animate-in fade-in slide-in-from-bottom-4 duration-700 space-y-8 pt-8 border-t border-border/50">
                    <div className="flex flex-col md:flex-row gap-8 items-start">
                      <div className="w-full md:w-56 aspect-video rounded-2xl bg-muted flex-shrink-0 overflow-hidden relative group shadow-2xl">
                        <img src={parseResult.cover_url || "https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&q=80&w=200"} alt="Thumbnail" className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
                        <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                          <Play className="w-8 h-8 text-white fill-current" />
                        </div>
                      </div>
                      <div className="flex-1 space-y-3">
                        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-primary/10 text-primary text-[10px] font-black uppercase tracking-widest mb-2">
                           {parseResult.source_site || "Web"}
                        </div>
                        <h3 className="font-extrabold text-2xl leading-tight line-clamp-2">{parseResult.title}</h3>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground font-medium">
                          <span className="flex items-center gap-1.5"><Clock className="w-4 h-4" /> {Math.floor(parseResult.duration_seconds / 60)}:{(parseResult.duration_seconds % 60).toString().padStart(2, '0')}</span>
                          <span className="flex items-center gap-1.5"><BarChart3 className="w-4 h-4" /> {parseResult.formats.length} 种格式</span>
                        </div>
                      </div>
                    </div>

                    <div>
                      <div className="text-sm font-bold text-muted-foreground mb-4 uppercase tracking-widest">选择下载规格</div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                        {(parseResult.formats || []).slice(0, 6).map((format: VideoFormat) => (
                          <button 
                            key={format.format_id} 
                            onClick={() => createTaskMutation.mutate(format.format_id)}
                            disabled={createTaskMutation.isPending}
                            className={cn(
                              "px-5 py-4 rounded-2xl border border-border text-sm font-bold transition-all text-left group hover:border-primary hover:shadow-xl hover:-translate-y-1 disabled:opacity-50 relative overflow-hidden",
                              format.kind === "recommended" ? "border-primary/50 bg-primary/5 ring-1 ring-primary/20" : "bg-card/30 backdrop-blur-sm"
                            )}
                          >
                            {format.kind === "recommended" && (
                              <div className="absolute top-0 right-0 p-1 bg-primary text-[8px] text-primary-foreground font-black uppercase rounded-bl-lg">推荐</div>
                            )}
                            <div className="text-[10px] text-muted-foreground mb-1 group-hover:text-primary transition-colors uppercase tracking-wider">{format.quality_label || format.resolution}</div>
                            <div className="line-clamp-1 group-hover:text-primary transition-colors">{format.label}</div>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Recent Tasks */}
            <div className="p-10 rounded-[2rem] border border-border bg-card/30 backdrop-blur-xl shadow-sm">
               <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
                <List className="w-6 h-6 text-primary" /> 活动流水线
              </h2>
              <div className="space-y-6">
                {isLoadingTasks ? (
                  <div className="text-center py-12 text-muted-foreground flex flex-col items-center gap-4">
                    <Loader2 className="w-8 h-8 animate-spin text-primary" />
                    <span className="font-bold tracking-widest uppercase text-xs">正在连接数据源...</span>
                  </div>
                ) : (tasksData || []).length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground border-2 border-dashed border-border rounded-3xl">
                    暂无活动任务
                  </div>
                ) : (tasksData || []).map((task: Task) => (
                  <div key={task.id} className="p-6 rounded-[1.5rem] border border-border hover:border-primary/30 bg-card/50 hover:shadow-2xl hover:shadow-primary/5 transition-all group">
                    <div className="flex justify-between items-start mb-6">
                      <div className="space-y-1">
                        <span className="font-bold text-lg line-clamp-1 group-hover:text-primary transition-colors">{task.title || task.id}</span>
                        <div className="text-[10px] text-muted-foreground uppercase font-black tracking-[0.2em]">ID: {task.id.slice(0, 8)}</div>
                      </div>
                      <div className="flex items-center gap-3">
                        {task.state === "succeeded" && (
                          <button 
                            onClick={() => { setSelectedTask(task); setIsAIModalOpen(true); }}
                            className="flex items-center gap-2 text-[10px] font-black uppercase px-3 py-1.5 rounded-xl bg-purple-500/10 text-purple-500 border border-purple-500/20 hover:bg-purple-500 hover:text-white transition-all shadow-lg shadow-purple-500/10"
                          >
                            <Sparkles className="w-3.5 h-3.5" /> AI 洞察
                          </button>
                        )}
                        <span className={cn(
                          "text-[10px] font-black uppercase px-3 py-1.5 rounded-xl flex items-center gap-2 border",
                          task.state === "succeeded" ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" : "bg-blue-500/10 text-blue-500 border-blue-500/20"
                        )}>
                          {task.state === "succeeded" ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                          {task.state === "succeeded" ? "已就绪" : "正在处理"}
                        </span>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-xs font-bold uppercase tracking-widest text-muted-foreground">
                        <span>同步进度</span>
                        <span>{task.progress}%</span>
                      </div>
                      <div className="h-3 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden p-0.5 shadow-inner">
                        <div className="h-full bg-gradient-to-r from-primary to-blue-400 rounded-full transition-all duration-700 relative" style={{ width: `${task.progress}%` }}>
                          <div className="absolute top-0 right-0 w-4 h-full bg-white/20 animate-pulse" />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* AI Tools Panel */}
          <div className="lg:col-span-4 space-y-10">
            <div className="p-8 rounded-[2rem] border border-border glass relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full blur-3xl" />
              
              <h2 className="text-xl font-bold mb-8 flex items-center gap-3">
                <Brain className="w-6 h-6 text-purple-500" /> AI 创作者套件
              </h2>
              <div className="space-y-4">
                {[
                  { name: "内容极简总结", icon: MessageSquare, desc: "精准提取视频精华观点。", beta: false, color: "text-blue-500" },
                  { name: "结构化思维导图", icon: Map, desc: "一键生成逻辑视觉导图。", beta: true, color: "text-purple-500" },
                  { name: "海量批量分析", icon: BarChart3, desc: "深度解析播放列表趋势。", beta: true, color: "text-emerald-500" },
                ].map((tool) => (
                  <button key={tool.name} className="w-full text-left p-5 rounded-[1.5rem] border border-border bg-card/30 hover:bg-card hover:border-primary/30 hover:-translate-y-1 transition-all group shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <tool.icon className={cn("w-6 h-6 transition-transform group-hover:scale-125 duration-500", tool.color)} />
                      {tool.beta && <span className="text-[9px] font-black px-2 py-1 rounded-md bg-purple-500/10 text-purple-500 uppercase tracking-widest">BETA</span>}
                    </div>
                    <div className="font-bold text-sm mb-1">{tool.name}</div>
                    <div className="text-xs text-muted-foreground leading-relaxed">{tool.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="p-8 rounded-[2rem] bg-gradient-to-br from-primary to-indigo-600 text-white shadow-2xl shadow-primary/30 relative overflow-hidden group">
               <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-150 transition-transform duration-1000 rotate-12">
                  <Sparkles className="w-40 h-40" />
               </div>
               <div className="relative z-10">
                 <h3 className="font-black text-2xl uppercase tracking-tight italic">Pro Version</h3>
                 <p className="text-white/80 text-sm mt-3 font-medium leading-relaxed">开启深度逻辑推理与无限量 AI 创作配额，让灵感不再受限。</p>
                 <button className="w-full mt-8 py-4 rounded-2xl bg-white text-primary font-black text-sm hover:shadow-2xl hover:scale-[1.02] active:scale-95 transition-all">立即开启订阅</button>
               </div>
            </div>
          </div>
        </div>

        {/* AI Results Modal */}
        {isAIModalOpen && selectedTask && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-8 bg-black/80 backdrop-blur-xl animate-in fade-in duration-500">
            <div className="bg-card border border-white/10 w-full max-w-5xl max-h-[90vh] rounded-[2.5rem] shadow-[0_0_100px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col animate-in zoom-in-95 duration-500">
              <div className="p-8 border-b border-border flex justify-between items-center bg-slate-50/50 dark:bg-slate-900/50">
                <div className="flex items-center gap-5">
                  <div className="p-4 rounded-[1.25rem] bg-purple-500 text-white shadow-xl shadow-purple-500/20 animate-float">
                    <Brain className="w-8 h-8" />
                  </div>
                  <div>
                    <h3 className="font-black text-2xl line-clamp-1">{selectedTask.title || selectedTask.id}</h3>
                    <p className="text-xs font-bold text-muted-foreground uppercase tracking-[0.3em] mt-1">Intelligence Insight Engine</p>
                  </div>
                </div>
                <button 
                  onClick={() => setIsAIModalOpen(false)}
                  className="p-3 rounded-2xl hover:bg-muted transition-all active:scale-90"
                >
                  <ChevronRight className="w-8 h-8 rotate-90" />
                </button>
              </div>
              
              <div className="flex-1 overflow-y-auto p-10 space-y-12">
                <section className="animate-in fade-in slide-in-from-bottom-8 duration-700 delay-200">
                  <h4 className="text-xl font-black mb-6 flex items-center gap-3 uppercase tracking-wider text-gradient">
                    <FileText className="w-6 h-6 text-primary" /> 执行摘要
                  </h4>
                  <div className="prose prose-lg prose-slate dark:prose-invert max-w-none p-10 rounded-[2rem] bg-slate-50/50 dark:bg-white/5 border border-white/10 shadow-inner leading-relaxed font-medium">
                    <ReactMarkdown>{selectedTask.ai_summary}</ReactMarkdown>
                  </div>
                </section>

                <section className="animate-in fade-in slide-in-from-bottom-8 duration-700 delay-400">
                  <h4 className="text-xl font-black mb-6 flex items-center gap-3 uppercase tracking-wider text-gradient">
                    <Map className="w-6 h-6 text-primary" /> 逻辑视觉地图
                  </h4>
                  <div className="p-10 rounded-[2rem] bg-white dark:bg-black/20 border border-border overflow-hidden">
                    <Mermaid chart={selectedTask.ai_mindmap || ""} />
                  </div>
                </section>
              </div>

              <div className="p-8 border-t border-border flex flex-col md:flex-row justify-between items-center gap-6 bg-slate-50/50 dark:bg-slate-900/50">
                <div className="flex items-center gap-8 text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                   <span className="flex items-center gap-2"><Sparkles className="w-4 h-4 text-purple-500" /> DeepSeek V3 Optimized</span>
                   <span className="flex items-center gap-2"><Clock className="w-4 h-4 text-blue-500" /> Ultra-fast processing</span>
                </div>
                <div className="flex gap-4 w-full md:w-auto">
                  <button className="flex-1 md:flex-none px-8 py-3 rounded-2xl border border-border hover:bg-muted transition-all font-bold text-sm">导出报告</button>
                  <button className="flex-1 md:flex-none px-10 py-3 rounded-2xl bg-primary text-primary-foreground font-black text-sm hover:shadow-2xl transition-all">复制成果</button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
order hover:bg-muted transition-colors font-medium">导出 PDF</button>
                  <button className="px-6 py-2 rounded-lg bg-primary text-primary-foreground font-bold hover:shadow-lg transition-all">复制文本</button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Workbench;
