import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Brain } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

import { TaskHeader } from "@/components/task-detail/TaskHeader";
import { TaskSummary } from "@/components/task-detail/TaskSummary";
import { TaskMindmap } from "@/components/task-detail/TaskMindmap";
import { TaskActions } from "@/components/task-detail/TaskActions";

interface Task {
  id: string;
  source_url: string;
  title: string | null;
  cover_url: string | null;
  duration_seconds: number | null;
  format_id: string | null;
  format_label: string | null;
  state: "pending" | "processing" | "succeeded" | "failed";
  progress: number;
  ai_summary: string | null;
  ai_mindmap: string | null;
  created_at: string;
}

const TaskDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: task, isLoading, error } = useQuery<Task>({
    queryKey: ["task", id],
    queryFn: async () => {
      const res = await api.get(`/tasks/${id}`);
      return res.data;
    },
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      return state === "pending" || state === "processing" ? 3000 : false;
    }
  });

  const handleExportPDF = async () => {
    if (task) {
      try {
        const response = await api.get(`/tasks/${task.id}/pdf`, {
          responseType: "blob",
        });
        const blob = new Blob([response.data], { type: "application/pdf" });
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = downloadUrl;
        link.setAttribute("download", `${task.title || "ai-report"}.pdf`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(downloadUrl);
      } catch (err) {
        console.error("Failed to export PDF", err);
      }
    }
  };

  const handleDownloadVideo = async () => {
    if (task) {
      try {
        const res = await api.get(`/tasks/${task.id}/download-link`);
        // Use direct window location assignment to download files directly, bypassing browser popup blockers
        window.location.href = res.data.url;
      } catch (err) {
        console.error("Failed to fetch download link", err);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 dark:bg-slate-950 gap-4">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
        <p className="text-xs font-black uppercase tracking-widest text-muted-foreground">正在加载 AI 洞察报告...</p>
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 dark:bg-slate-950 gap-6 px-4 text-center">
        <div className="w-16 h-16 rounded-[1.5rem] bg-red-500/10 text-red-500 flex items-center justify-center shadow-lg">
          <Brain className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-black">获取任务详情失败</h2>
          <p className="text-sm text-muted-foreground max-w-sm">无法加载此 AI 洞察报告，任务可能已被删除或网络连接存在问题。</p>
        </div>
        <Button onClick={() => navigate("/workbench")} className="rounded-xl font-bold px-6">
          返回工作台
        </Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950/20 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-10">
        
        {/* Navigation Action */}
        <div className="flex items-center justify-between">
          <Button 
            variant="ghost" 
            className="rounded-xl font-bold hover:bg-slate-100 dark:hover:bg-slate-900 group"
            onClick={() => navigate("/workbench")}
          >
            <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" /> 返回工作台
          </Button>
          
          <span className="text-[10px] font-black uppercase tracking-[0.3em] text-muted-foreground bg-slate-100 dark:bg-slate-900/50 px-4 py-1.5 rounded-full border border-slate-200/40 dark:border-slate-800/40">
            Intelligence Report System
          </span>
        </div>

        {/* Modular Decoupled Sub-components */}
        <TaskHeader task={task} onDownloadVideo={handleDownloadVideo} />

        {task.state === "succeeded" ? (
          <div className="space-y-12 pt-4 animate-in fade-in slide-in-from-bottom-6 duration-700">
            {task.ai_summary && <TaskSummary summary={task.ai_summary} />}
            {task.ai_mindmap && <TaskMindmap mindmap={task.ai_mindmap} />}
            <TaskActions summary={task.ai_summary || ""} onExportPDF={handleExportPDF} />
          </div>
        ) : (
          <div className="p-16 rounded-[2.5rem] bg-white dark:bg-slate-900 border border-slate-200/50 dark:border-slate-800/80 text-center space-y-6 shadow-sm">
            <div className="w-16 h-16 rounded-[1.5rem] bg-purple-500/10 text-purple-600 flex items-center justify-center mx-auto animate-pulse">
              <Brain className="w-8 h-8" />
            </div>
            <div className="space-y-2">
              <h3 className="text-xl font-black">AI 正在深度解析中...</h3>
              <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                任务状态：{task.state === "pending" ? "等待排队中" : `正在提取视频并由 AI 深度解析中 (${task.progress}%)`}
              </p>
            </div>
            <div className="max-w-xs mx-auto bg-slate-100 dark:bg-slate-950 rounded-full h-3 overflow-hidden">
              <div 
                className="bg-primary h-full rounded-full transition-all duration-500" 
                style={{ width: `${task.progress}%` }} 
              />
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default TaskDetail;
