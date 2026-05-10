import { Search, List, BarChart3, Settings, Brain, MessageSquare, Map, Download, CheckCircle2, Clock, Sparkles, FileText, ChevronRight } from "lucide-react";
import { cn } from "../lib/utils";
import ReactMarkdown from "react-markdown";
import Mermaid from "../components/Mermaid";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

const Workbench: React.FC = () => {
  const [url, setUrl] = useState("");
  const [step, setStep] = useState(1); // 1: Input, 2: Selection
  const [parseResult, setParseResult] = useState<any>(null);
  const [selectedTask, setSelectedTask] = useState<any>(null);
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
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 md:p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">创作者工作台</h1>
            <p className="text-muted-foreground mt-1">轻松管理您的视频处理流水线。</p>
          </div>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-card hover:bg-muted transition-all">
              <Settings className="w-4 h-4" /> 设置
            </button>
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-md">
              升级专业版
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Control Panel */}
          <div className="lg:col-span-2 space-y-6">
            <div className="p-6 rounded-2xl border border-border bg-card shadow-sm backdrop-blur-xl bg-white/50 dark:bg-black/50">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Search className="w-5 h-5 text-primary" /> 新建任务
              </h2>
              <div className="space-y-4">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="粘贴视频链接 (YouTube, Bilibili, TikTok...)"
                    className="w-full px-4 py-4 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary outline-none transition-all pr-32"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                  />
                  <button 
                    onClick={handleAnalyze}
                    disabled={!url || parseMutation.isPending}
                    className="absolute right-2 top-2 bottom-2 px-6 rounded-lg bg-primary text-primary-foreground font-medium disabled:opacity-50 transition-all"
                  >
                    {parseMutation.isPending ? "解析中..." : "解析"}
                  </button>
                </div>

                {step === 2 && parseResult && (
                  <div className="animate-in fade-in slide-in-from-top-4 duration-500 space-y-6 pt-4 border-t border-border">
                    <div className="flex gap-4">
                      <div className="w-32 h-20 rounded-lg bg-muted flex-shrink-0 overflow-hidden relative group">
                        <img src={parseResult.cover_url || "https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&q=80&w=200"} alt="Thumbnail" className="w-full h-full object-cover group-hover:scale-110 transition-transform" />
                        <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
                          <Clock className="w-4 h-4 text-white" />
                        </div>
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg line-clamp-1">{parseResult.title}</h3>
                        <p className="text-sm text-muted-foreground mt-1">来源: {parseResult.source_site || "Web"} • 时长: {Math.floor(parseResult.duration_seconds / 60)}:{(parseResult.duration_seconds % 60).toString().padStart(2, '0')}</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {(parseResult.formats || []).slice(0, 6).map((format: any) => (
                        <button 
                          key={format.format_id} 
                          onClick={() => createTaskMutation.mutate(format.format_id)}
                          disabled={createTaskMutation.isPending}
                          className={cn(
                            "px-4 py-3 rounded-xl border border-border text-sm font-medium transition-all text-left group hover:border-primary disabled:opacity-50",
                            format.kind === "recommended" ? "border-primary bg-primary/5" : "bg-card"
                          )}
                        >
                          <div className="text-xs text-muted-foreground mb-1 group-hover:text-primary/70">{format.quality_label || format.resolution}</div>
                          <div className="line-clamp-1">{format.label}</div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Recent Tasks */}
            <div className="p-6 rounded-2xl border border-border bg-card shadow-sm">
               <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <List className="w-5 h-5 text-primary" /> 活动任务
              </h2>
              <div className="space-y-4">
                {isLoadingTasks ? (
                  <div className="text-center py-8 text-muted-foreground">加载任务中...</div>
                ) : (tasksData || []).map((task: any) => (
                  <div key={task.id} className="p-4 rounded-xl border border-border hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors">
                    <div className="flex justify-between items-center mb-3">
                      <span className="font-medium line-clamp-1">{task.title || task.id}</span>
                      <div className="flex items-center gap-3">
                        {task.state === "succeeded" && (
                          <button 
                            onClick={() => { setSelectedTask(task); setIsAIModalOpen(true); }}
                            className="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-md bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400 border border-purple-100 dark:border-purple-800 hover:bg-purple-100 transition-colors"
                          >
                            <Sparkles className="w-3 h-3" /> AI 洞察
                          </button>
                        )}
                        <span className={cn(
                          "text-xs px-2 py-1 rounded-full flex items-center gap-1 uppercase",
                          task.state === "succeeded" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                        )}>
                          {task.state === "succeeded" ? <CheckCircle2 className="w-3 h-3" /> : <Clock className="w-3 h-3 animate-spin" />}
                          {task.state === "succeeded" ? "已完成" : "进行中"}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex-1 h-2 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                        <div className="h-full bg-primary transition-all duration-500" style={{ width: `${task.progress}%` }} />
                      </div>
                      <span className="text-xs text-muted-foreground w-12 text-right">{task.progress}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* AI Tools Panel */}
          <div className="space-y-6">
            <div className="p-6 rounded-2xl border border-border bg-card shadow-sm">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <Brain className="w-5 h-5 text-purple-500" /> 全局 AI 工具
              </h2>
              <div className="space-y-3">
                {[
                  { name: "AI 总结", icon: MessageSquare, desc: "通过 URL 快速总结视频内容。", beta: false },
                  { name: "思维导图", icon: Map, desc: "即时生成视频内容的视觉结构。", beta: true },
                  { name: "批量分析", icon: BarChart3, desc: "一次性处理整个播放列表。", beta: true },
                ].map((tool) => (
                  <button key={tool.name} className="w-full text-left p-4 rounded-xl border border-border hover:bg-slate-50 dark:hover:bg-slate-900 transition-all group relative overflow-hidden">
                    <div className="flex items-center justify-between mb-1">
                      <tool.icon className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
                      {tool.beta && <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">测试版</span>}
                    </div>
                    <div className="font-semibold text-sm">{tool.name}</div>
                    <div className="text-xs text-muted-foreground mt-1">{tool.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-gradient-to-br from-primary to-blue-600 text-white shadow-lg relative overflow-hidden group">
               <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-125 transition-transform duration-700">
                  <Sparkles className="w-24 h-24" />
               </div>
               <h3 className="font-bold text-lg relative z-10">专业版智能</h3>
               <p className="text-white/80 text-sm mt-2 relative z-10">解锁深度推理和无限视频思维导图。</p>
               <button className="w-full mt-4 py-2 rounded-lg bg-white text-primary font-bold text-sm relative z-10 hover:bg-opacity-90 transition-all">立即升级</button>
            </div>
          </div>
        </div>

        {/* AI Results Modal */}
        {isAIModalOpen && selectedTask && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
            <div className="bg-card border border-border w-full max-w-4xl max-h-[90vh] rounded-3xl shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-300">
              <div className="p-6 border-b border-border flex justify-between items-center bg-slate-50/50 dark:bg-slate-900/50">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-purple-100 text-purple-600 dark:bg-purple-900/30">
                    <Brain className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-bold text-xl">{selectedTask.title || selectedTask.id}</h3>
                    <p className="text-sm text-muted-foreground">AI 智能分析洞察</p>
                  </div>
                </div>
                <button 
                  onClick={() => setIsAIModalOpen(false)}
                  className="p-2 rounded-full hover:bg-muted transition-colors"
                >
                  <ChevronRight className="w-6 h-6 rotate-90 md:rotate-0" />
                </button>
              </div>
              
              <div className="flex-1 overflow-y-auto p-6 space-y-8">
                <section>
                  <h4 className="text-lg font-bold mb-4 flex items-center gap-2">
                    <FileText className="w-5 h-5 text-primary" /> 内容执行摘要
                  </h4>
                  <div className="prose prose-slate dark:prose-invert max-w-none p-6 rounded-2xl bg-slate-50/50 dark:bg-slate-900/50 border border-border">
                    <ReactMarkdown>{selectedTask.ai_summary}</ReactMarkdown>
                  </div>
                </section>

                <section>
                  <h4 className="text-lg font-bold mb-4 flex items-center gap-2">
                    <Map className="w-5 h-5 text-primary" /> 视觉思维导图
                  </h4>
                  <Mermaid chart={selectedTask.ai_mindmap} />
                </section>
              </div>

              <div className="p-6 border-t border-border flex justify-between items-center bg-slate-50/50 dark:bg-slate-900/50">
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                   <span className="flex items-center gap-1"><Sparkles className="w-3 h-3" /> DeepSeek V3</span>
                   <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> 2秒 处理完成</span>
                </div>
                <div className="flex gap-2">
                  <button className="px-4 py-2 rounded-lg border border-border hover:bg-muted transition-colors font-medium">导出 PDF</button>
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
