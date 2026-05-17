import React, { useState } from "react";
import { Search, List, BarChart3, Settings, Brain, MessageSquare, Map, CheckCircle2, Clock, Sparkles, Play, Loader2, Download } from "lucide-react";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

interface VideoFormat {
  format_id: string;
  quality_label?: string;
  resolution?: string;
  label: string;
  kind?: string;
}

interface ParseResult {
  title: string;
  duration_seconds: number;
  cover_url: string;
  source_site: string;
  formats: VideoFormat[];
}

interface Task {
  id: string;
  title: string;
  state: "pending" | "processing" | "succeeded" | "failed";
  progress: number;
  ai_summary?: string;
  ai_mindmap?: string;
}

const Workbench: React.FC = () => {
  const [url, setUrl] = useState("");
  const [step, setStep] = useState(1);
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const navigate = useNavigate();

  const queryClient = useQueryClient();

  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoadingTasks, setIsLoadingTasks] = useState(true);

  React.useEffect(() => {
    // Initial fetch
    api.get("/tasks")
      .then(res => {
        setTasks(res.data);
        setIsLoadingTasks(false);
      })
      .catch(err => {
        console.error("Failed to fetch tasks:", err);
        setIsLoadingTasks(false);
      });

    // SSE connection
    const token = localStorage.getItem("auth_token");
    const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
    const eventSource = new EventSource(`${apiBase}/tasks/stream?token=${token}`);

    eventSource.addEventListener("tasks", (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "tasks") {
        setTasks(data.tasks);
      }
    });

    eventSource.onerror = () => {
      eventSource.close();
      // Fallback or retry logic can go here
    };

    return () => eventSource.close();
  }, []);

  const parseMutation = useMutation({
    mutationFn: async (url: string) => {
      const res = await api.post("/parse", { url });
      return res.data;
    },
    onSuccess: (data) => {
      setParseResult(data);
      setStep(2);
    },
  });

  const createTaskMutation = useMutation({
    mutationFn: async (formatId: string) => {
      const res = await api.post("/tasks", {
        url: url,
        format_id: formatId,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      setStep(1);
      setUrl("");
      setParseResult(null);
    },
  });

  const handleAnalyze = () => {
    if (!url) return;
    parseMutation.mutate(url);
  };

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-12">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-1">
            <h1 className="text-4xl font-black tracking-tight">控制中心</h1>
            <p className="text-muted-foreground text-lg">高效管理您的视频解析与智能处理任务。</p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="lg" className="rounded-2xl gap-2 font-bold">
              <Settings className="w-5 h-5" /> 配置
            </Button>
            <Button size="lg" className="rounded-2xl font-black shadow-lg shadow-primary/20">
              升级专业版
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Main Action Area */}
          <div className="lg:col-span-8 space-y-8">
            <Card className="border-none shadow-xl rounded-[2.5rem] p-4 md:p-8 overflow-hidden relative group">
              <CardHeader className="pb-8">
                <CardTitle className="text-2xl font-black flex items-center gap-3">
                  <Search className="w-6 h-6 text-primary" /> 开始新任务
                </CardTitle>
                <CardDescription className="text-base">输入视频链接，由 AI 接管后续一切工作。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
                <div className="flex gap-4">
                  <Input 
                    placeholder="粘贴视频链接 (YouTube, Bilibili, TikTok...)" 
                    className="h-14 rounded-2xl text-base px-6 border-slate-200 bg-slate-50/50 focus-visible:ring-primary/20"
                    value={url}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUrl(e.target.value)}
                  />
                  <Button 
                    size="lg" 
                    className="h-14 px-10 rounded-2xl font-black"
                    onClick={handleAnalyze}
                    disabled={!url || parseMutation.isPending}
                  >
                    {parseMutation.isPending ? "分析中..." : "解析视频"}
                  </Button>
                </div>

                {step === 2 && parseResult && (
                  <div className="pt-8 border-t border-slate-100 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="flex flex-col md:flex-row gap-8">
                      <div className="w-full md:w-56 aspect-video rounded-3xl bg-slate-100 overflow-hidden relative shadow-lg">
                        <img src={parseResult.cover_url} alt="Cover" className="w-full h-full object-cover" />
                        <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
                          <Play className="w-8 h-8 text-white fill-current" />
                        </div>
                      </div>
                      <div className="flex-1 space-y-3">
                        <Badge variant="secondary" className="rounded-lg font-bold px-3 py-1 uppercase tracking-widest text-[10px]">
                          {parseResult.source_site}
                        </Badge>
                        <h3 className="text-2xl font-black leading-tight line-clamp-2">{parseResult.title}</h3>
                        <div className="flex items-center gap-4 text-sm font-bold text-muted-foreground">
                           <span className="flex items-center gap-1.5"><Clock className="w-4 h-4" /> {Math.floor(parseResult.duration_seconds / 60)}:{(parseResult.duration_seconds % 60).toString().padStart(2, '0')}</span>
                           <span className="flex items-center gap-1.5"><BarChart3 className="w-4 h-4" /> {parseResult.formats.length} 种规格</span>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-4">
                       <h4 className="text-sm font-black uppercase tracking-[0.2em] text-muted-foreground">选择下载质量</h4>
                       <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                          {parseResult.formats.slice(0, 6).map((format) => (
                            <Button 
                              key={format.format_id}
                              variant={format.kind === "recommended" ? "default" : "outline"}
                              className={cn(
                                "h-auto py-4 px-5 flex flex-col items-start gap-1 rounded-2xl border-2 transition-all hover:-translate-y-1",
                                format.kind === "recommended" ? "border-primary shadow-lg shadow-primary/10" : "border-slate-100 hover:border-primary/30"
                              )}
                              onClick={() => createTaskMutation.mutate(format.format_id)}
                              disabled={createTaskMutation.isPending}
                            >
                               <span className="text-[10px] uppercase font-black tracking-widest opacity-60">{format.quality_label || format.resolution}</span>
                               <span className="font-bold line-clamp-1">{format.label}</span>
                            </Button>
                          ))}
                       </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Task List */}
            <Card className="border-none shadow-xl rounded-[2.5rem] p-4 md:p-8">
               <CardHeader className="pb-8">
                <CardTitle className="text-2xl font-black flex items-center gap-3">
                  <List className="w-6 h-6 text-primary" /> 活动流水线
                </CardTitle>
                <CardDescription className="text-base">实时监控您的任务状态与 AI 处理进度。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {isLoadingTasks ? (
                  <div className="py-20 flex flex-col items-center justify-center gap-4 text-muted-foreground">
                    <Loader2 className="w-10 h-10 animate-spin text-primary" />
                    <span className="font-bold uppercase tracking-widest text-xs">正在同步数据...</span>
                  </div>
                ) : (tasks || []).length === 0 ? (
                   <div className="py-20 border-4 border-dashed border-slate-50 rounded-[2rem] text-center">
                      <p className="text-muted-foreground font-bold">暂无活动任务</p>
                   </div>
                ) : (tasks || []).map((task: Task) => (
                  <div key={task.id} className="p-6 rounded-[2rem] border-2 border-slate-50 hover:border-primary/20 hover:bg-slate-50/50 transition-all group">
                    <div className="flex justify-between items-start mb-6">
                      <div className="space-y-1">
                        <h4 className="font-black text-lg group-hover:text-primary transition-colors">{task.title || task.id}</h4>
                        <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground opacity-60">ID: {task.id.slice(0, 8)}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        {task.state === "succeeded" && (
                          <div className="flex gap-2">
                            <Button 
                              variant="secondary" 
                              size="sm" 
                              className="rounded-xl font-black text-[10px] h-8 gap-2 bg-blue-500/10 text-blue-600 hover:bg-blue-500 hover:text-white transition-all"
                              onClick={async () => {
                                const res = await api.get(`/tasks/${task.id}/download-link`);
                                window.open(res.data.url, "_blank");
                              }}
                            >
                              <Download className="w-3.5 h-3.5" /> 下载视频
                            </Button>
                            <Button 
                              variant="secondary" 
                              size="sm" 
                              className="rounded-xl font-black text-[10px] h-8 gap-2 bg-purple-500/10 text-purple-600 hover:bg-purple-500 hover:text-white transition-all"
                              onClick={() => navigate(`/workbench/task/${task.id}`)}
                            >
                              <Sparkles className="w-3.5 h-3.5" /> AI 洞察
                            </Button>
                          </div>
                        )}
                        <Badge variant={task.state === "succeeded" ? "default" : "secondary"} className="rounded-xl px-3 py-1 font-black text-[10px] uppercase tracking-widest h-8 flex items-center gap-2">
                           {task.state === "succeeded" ? <CheckCircle2 className="w-3 h-3" /> : <Loader2 className="w-3 h-3 animate-spin" />}
                           {task.state === "succeeded" ? "已就绪" : "处理中"}
                        </Badge>
                      </div>
                    </div>
                    <div className="space-y-3">
                       <div className="flex justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                          <span>处理进度</span>
                          <span>{task.progress}%</span>
                       </div>
                       <Progress value={task.progress} className="h-3 rounded-full bg-slate-100" />
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-4 space-y-8">
             <Card className="border-none shadow-xl rounded-[2.5rem] p-4 md:p-8 bg-slate-900 text-white">
                <CardHeader className="pb-8">
                  <CardTitle className="text-2xl font-black flex items-center gap-3">
                    <Brain className="w-6 h-6 text-primary" /> 创作者工具
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                   {[
                     { name: "极简视频摘要", desc: "精准提取核心观点。", icon: MessageSquare },
                     { name: "思维导图生成", desc: "可视化知识架构。", icon: Map, beta: true },
                     { name: "海量批量处理", desc: "支持整个播放列表。", icon: BarChart3, beta: true },
                   ].map((tool) => (
                     <button key={tool.name} className="w-full text-left p-5 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 transition-all group">
                        <div className="flex items-center justify-between mb-2">
                           <tool.icon className="w-5 h-5 text-primary group-hover:scale-125 transition-transform" />
                           {tool.beta && <Badge className="rounded-lg bg-primary/20 text-primary border-none font-black text-[8px] h-5 uppercase">Beta</Badge>}
                        </div>
                        <div className="font-bold text-sm">{tool.name}</div>
                        <div className="text-xs text-white/50">{tool.desc}</div>
                     </button>
                   ))}
                </CardContent>
             </Card>

             <Card className="border-none shadow-xl rounded-[2.5rem] p-8 bg-primary text-primary-foreground relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-10 rotate-12 group-hover:scale-150 transition-transform duration-1000">
                   <Sparkles className="w-40 h-40" />
                </div>
                <div className="relative z-10 space-y-6">
                   <h3 className="text-2xl font-black italic uppercase tracking-tighter">Pro Plus</h3>
                   <p className="text-sm font-medium leading-relaxed opacity-90">解锁无限次 AI 深度分析、4K 超清并发下载以及长达 30 天的云端存储。</p>
                   <Button variant="secondary" className="w-full h-14 rounded-2xl font-black text-sm hover:scale-[1.02] transition-transform shadow-xl">立即开启权益</Button>
                </div>
             </Card>
          </div>
        </div>
      </div>


    </div>
  );
};

export default Workbench;
