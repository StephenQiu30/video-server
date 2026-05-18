import React, { useState } from "react";
import {
  Activity,
  Brain,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Loader2,
  MessageCircle,
  Search,
  Download,
  Play,
  ShieldCheck,
  ListChecks,
  LineChart,
  PlayCircle,
  Sparkles,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
}

const taskStateConfig: Record<
  Task["state"],
  {
    text: string;
    tone: "secondary" | "default" | "destructive";
    icon: React.ReactNode;
    description: string;
  }
> = {
  pending: {
    text: "等待开始",
    tone: "secondary",
    icon: <Clock3 className="h-3.5 w-3.5" />,
    description: "任务已提交，等待系统调度",
  },
  processing: {
    text: "处理中",
    tone: "secondary",
    icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
    description: "下载与转换任务进行中",
  },
  succeeded: {
    text: "已完成",
    tone: "default",
    icon: <CheckCircle2 className="h-3.5 w-3.5" />,
    description: "任务完成，可下载内容",
  },
  failed: {
    text: "失败",
    tone: "destructive",
    icon: <ShieldCheck className="h-3.5 w-3.5" />,
    description: "执行失败，请检查链接或重试",
  },
};

const statusDotClass: Record<Task["state"], string> = {
  pending: "bg-amber-500",
  processing: "bg-sky-500",
  succeeded: "bg-emerald-500",
  failed: "bg-rose-500",
};

const Workbench: React.FC = () => {
  const [url, setUrl] = useState("");
  const [step, setStep] = useState(1);
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const navigate = useNavigate();

  const queryClient = useQueryClient();

  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoadingTasks, setIsLoadingTasks] = useState(true);

  React.useEffect(() => {
    api.get("/tasks")
      .then((res) => {
        setTasks(res.data);
        setIsLoadingTasks(false);
      })
      .catch((err) => {
        console.error("Failed to fetch tasks:", err);
        setIsLoadingTasks(false);
      });

    const token = localStorage.getItem("auth_token");
    const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
    const eventSource = new EventSource(`${apiBase}/tasks/stream?token=${token}`);

    eventSource.addEventListener("tasks", (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "tasks") {
        setTasks(data.tasks);
      }
    });

    return () => {
      eventSource.close();
    };
  }, []);

  const parseMutation = useMutation({
    mutationFn: async (targetUrl: string) => {
      const res = await api.post("/parse", { url: targetUrl });
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
        url,
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

  const durationLabel = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = String(seconds % 60).padStart(2, "0");
    return `${mins}:${secs}`;
  };

  const handleAnalyze = () => {
    if (!url.trim()) return;
    parseMutation.mutate(url);
  };

  const totalTasks = tasks.length;
  const successTasks = tasks.filter((item) => item.state === "succeeded").length;
  const runningTasks = tasks.filter((item) => item.state === "processing").length;

  return (
    <div className="min-h-screen bg-[#eef6ff] py-8 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <section className="rounded-3xl border border-sky-100/80 bg-white/85 p-6 shadow-sm ring-1 ring-white/70 backdrop-blur">
          <div className="flex flex-wrap items-end justify-between gap-5">
            <div className="space-y-3">
              <p className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-1 text-xs font-semibold tracking-[0.14em] text-sky-700 uppercase">
                <Activity className="h-3.5 w-3.5" />
                工作台
              </p>
              <h1 className="text-3xl font-semibold text-slate-900 sm:text-4xl">视频任务工作台</h1>
              <p className="max-w-2xl text-sm leading-6 text-slate-500">
                统一入口处理“解析→转码→下载→复用”，让每一次任务从提交到归档都更可控。
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button
                variant="outline"
                size="sm"
                className="h-9 rounded-full border-sky-200 text-sky-700 hover:bg-sky-50"
                onClick={() => setStep(1)}
              >
                <Sparkles className="h-4 w-4" />
                重置新建流程
              </Button>
              <Button variant="secondary" size="sm" className="h-9 rounded-full text-sky-800">
                <LineChart className="h-4 w-4" />
                运行监控
              </Button>
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="space-y-6">
            <Card className="border-slate-200 bg-white/95">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-xl text-slate-900">
                  <Search className="h-5 w-5 text-sky-600" />
                  新建任务
                </CardTitle>
                <CardDescription className="text-slate-600">输入视频链接后快速生成下载任务。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 lg:grid-cols-[1fr_auto]">
                  <div className="relative">
                    <Input
                      placeholder="粘贴视频链接（YouTube / B 站 / TikTok）"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      className="h-11 rounded-[14px] border-sky-200 bg-white text-slate-800 placeholder:text-slate-400"
                    />
                    <button
                      type="button"
                      aria-label="清空链接"
                      onClick={() => setUrl("")}
                      className={`absolute right-3 top-1/2 -translate-y-1/2 text-sm font-medium transition ${url ? "text-slate-500 hover:text-slate-700" : "invisible"}`}
                    >
                      清空
                    </button>
                  </div>
                  <Button
                    size="lg"
                    className="h-11 rounded-[14px] bg-sky-600 px-8 text-white shadow-sm hover:bg-sky-700"
                    onClick={handleAnalyze}
                    disabled={!url || parseMutation.isPending}
                  >
                    {parseMutation.isPending ? "解析中..." : "解析视频"}
                  </Button>
                </div>
                {parseMutation.isPending ? (
                  <div className="flex items-center gap-2 rounded-2xl border border-dashed border-sky-200 bg-sky-50/60 px-4 py-3 text-sm text-sky-700">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    正在读取元数据，请稍候。
                  </div>
                ) : null}

                {step === 2 && parseResult ? (
                  <div className="rounded-2xl border border-sky-100 bg-sky-50/70 p-4">
                    <div className="mb-4 flex flex-col gap-4 lg:flex-row lg:items-start">
                      <div className="relative h-32 min-h-32 w-full overflow-hidden rounded-xl border border-sky-100 bg-slate-100 lg:h-28 lg:w-56">
                        <img
                          src={parseResult.cover_url}
                          alt="视频封面"
                          className="h-full w-full object-cover"
                        />
                        <div className="absolute inset-0 bg-gradient-to-br from-black/35 to-black/10" />
                        <PlayCircle className="absolute left-3 top-3 h-4 w-4 text-white" />
                      </div>
                      <div className="min-w-0 flex-1 space-y-1.5">
                        <Badge className="rounded-full bg-sky-600/90 text-white hover:bg-sky-700/90">
                          {parseResult.source_site}
                        </Badge>
                        <h3 className="text-base font-medium leading-6 text-slate-900">{parseResult.title}</h3>
                        <p className="text-sm text-slate-600">
                          时长 {durationLabel(parseResult.duration_seconds)} · 可用规格 {parseResult.formats.length} 个
                        </p>
                        <p className="text-xs text-slate-500">确认后点击下面按钮即可开始创建下载任务。</p>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.14em] text-slate-500">
                        <span>选择导出规格</span>
                        <span>最多显示 6 个</span>
                      </div>
                      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                        {parseResult.formats.slice(0, 6).map((format) => (
                          <Button
                            key={format.format_id}
                            size="sm"
                            variant={format.kind === "recommended" ? "default" : "outline"}
                            className="h-auto items-start rounded-xl border-sky-200 px-3 py-2 text-left transition hover:-translate-y-0.5"
                            onClick={() => createTaskMutation.mutate(format.format_id)}
                            disabled={createTaskMutation.isPending}
                          >
                            <p className="text-[11px] uppercase tracking-[0.15em] text-sky-700">
                              {format.quality_label || format.resolution}
                            </p>
                            <p className="text-sm font-semibold text-slate-800">{format.label}</p>
                            <p className="text-xs text-slate-500">点击创建任务</p>
                          </Button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <Card className="border-slate-200 bg-white/95">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-xl text-slate-900">
                  <ListChecks className="h-5 w-5 text-sky-600" />
                  任务流水线
                </CardTitle>
                <CardDescription className="text-slate-600">并行监控全部任务，快速进入下载和复查。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {isLoadingTasks ? (
                  <div className="flex items-center justify-center gap-2 rounded-2xl bg-slate-50 py-8 text-sm text-slate-500">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    同步任务中…
                  </div>
                ) : tasks.length === 0 ? (
                  <div className="rounded-2xl border border-sky-100 bg-sky-50/60 px-4 py-8 text-center text-sm text-slate-500">
                    还没有任务，先去新建一个开始。
                  </div>
                ) : (
                  <div className="space-y-3">
                    {tasks.map((task) => {
                      const cfg = taskStateConfig[task.state];
                      return (
                        <div
                          key={task.id}
                          className="rounded-xl border border-slate-200 bg-white p-4 transition hover:border-sky-300"
                        >
                          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                            <div className="min-w-0 flex-1 space-y-1">
                              <div className="flex items-start gap-2">
                                <span
                                  className={`mt-1 inline-block h-2.5 w-2.5 shrink-0 rounded-full ${statusDotClass[task.state]}`}
                                />
                                <div className="min-w-0">
                                  <p className="text-sm font-medium text-slate-900">
                                    {task.title || `任务 ${task.id.slice(0, 8)}`}
                                  </p>
                                  <p className="text-xs text-slate-500">{cfg.description}</p>
                                </div>
                              </div>
                              <p className="ml-4.5 pl-2 text-[11px] uppercase tracking-[0.14em] text-slate-400">ID: {task.id.slice(0, 8)}</p>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge variant={cfg.tone} className="h-7 rounded-full px-3 text-[11px] uppercase tracking-[0.14em]">
                                {cfg.text}
                              </Badge>
                              {task.state === "succeeded" ? (
                                <Button
                                  size="sm"
                                  className="h-8 rounded-full bg-sky-50 px-3 text-xs text-sky-700 hover:bg-sky-100"
                                  onClick={async () => {
                                    const res = await api.get(`/tasks/${task.id}/download-link`);
                                    window.open(res.data.url, "_blank");
                                  }}
                                >
                                  <Download className="mr-1 h-3.5 w-3.5" />
                                  下载
                                </Button>
                              ) : null}

                              <Button
                                size="sm"
                                variant="outline"
                                className="h-8 rounded-full border-sky-200 text-sky-700 hover:bg-sky-50"
                                onClick={() => navigate(`/workbench/task/${task.id}`)}
                              >
                                <ChevronRight className="mr-1 h-3.5 w-3.5" />
                                详情
                              </Button>
                            </div>
                          </div>
                          <div className="mt-4 space-y-2">
                            <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.14em] text-slate-500">
                              <span>任务进度</span>
                              <span>{task.progress}%</span>
                            </div>
                            <Progress value={task.progress} className="h-2 rounded-full bg-sky-100/80" />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <aside className="space-y-6">
            <Card className="border-slate-200 bg-white/95">
              <CardHeader>
                <CardTitle className="text-lg text-slate-900">任务一览</CardTitle>
                <CardDescription className="text-slate-600">会话中的核心指标。</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-2">
                <div className="flex items-center justify-between rounded-xl border border-sky-100 bg-sky-50 p-3">
                  <span className="text-sm text-slate-600">总任务</span>
                  <span className="text-xl font-semibold text-slate-900">{totalTasks}</span>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-3">
                  <span className="text-sm text-slate-600">进行中</span>
                  <span className="text-xl font-semibold text-sky-700">{runningTasks}</span>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-3">
                  <span className="text-sm text-slate-600">已完成</span>
                  <span className="text-xl font-semibold text-emerald-700">{successTasks}</span>
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200 bg-white/95">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg text-slate-900">
                  <Brain className="h-5 w-5 text-sky-600" />
                  创作者工具
                </CardTitle>
                <CardDescription className="text-slate-600">和任务流结合的常用工具入口。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {[
                  { label: "任务摘要", hint: "提炼关键观点", icon: MessageCircle },
                  { label: "自动分幕", hint: "更适合课程复盘", icon: Brain },
                  { label: "转码校验", hint: "保障兼容性与稳定性", icon: ShieldCheck },
                ].map((tool) => (
                  <div
                    key={tool.label}
                    className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50/80 p-3"
                  >
                    <div>
                      <p className="text-sm font-medium text-slate-900">{tool.label}</p>
                      <p className="text-xs text-slate-500">{tool.hint}</p>
                    </div>
                    <tool.icon className="h-4 w-4 text-sky-600" />
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="border-slate-200 bg-sky-700/95 text-white">
              <CardHeader>
                <CardTitle className="text-lg">流程建议</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-sky-100">
                  完成任务后可直接在详情页查看日志、重试失败步骤，或一键归档到历史记录。
                </p>
                <div className="rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-xs text-sky-100">
                  <p>建议顺序：</p>
                  <p>1) 先解析 &nbsp;2) 选择规格 &nbsp;3) 观察进度 &nbsp;4) 下载归档</p>
                </div>
                <Button
                  variant="secondary"
                  className="w-full rounded-full bg-white/95 text-sky-700 hover:bg-white"
                  onClick={() => navigate("/")}
                >
                  <Play className="mr-2 h-4 w-4" />
                  回到首页总览
                </Button>
              </CardContent>
            </Card>
          </aside>
        </div>
      </div>
    </div>
  );
};

export default Workbench;
