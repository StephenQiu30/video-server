import React from "react";
import { Sparkles, Clock, ExternalLink, Download, Brain } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface Task {
  id: string;
  source_url: string;
  title: string | null;
  cover_url: string | null;
  duration_seconds: number | null;
  format_id: string | null;
  format_label: string | null;
  state: string;
  created_at: string;
}

interface TaskHeaderProps {
  task: Task;
  onDownloadVideo: () => void;
}

export const TaskHeader: React.FC<TaskHeaderProps> = ({ task, onDownloadVideo }) => {
  return (
    <Card className="border-none shadow-xl rounded-[2.5rem] overflow-hidden bg-white dark:bg-slate-900">
      <div className="flex flex-col md:flex-row">
        {/* Aspect Video Cover */}
        <div className="w-full md:w-80 aspect-video md:aspect-auto md:h-52 bg-slate-100 dark:bg-slate-950 overflow-hidden relative group">
          {task.cover_url ? (
            <img 
              src={task.cover_url} 
              alt="Cover" 
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" 
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-slate-100 dark:bg-slate-950">
              <Brain className="w-12 h-12 text-slate-300 dark:text-slate-700 animate-pulse" />
            </div>
          )}
          <div className="absolute inset-0 bg-black/10 flex items-center justify-center transition-opacity opacity-0 group-hover:opacity-100">
            <Sparkles className="w-8 h-8 text-white fill-current animate-float" />
          </div>
        </div>

        {/* Info details */}
        <div className="flex-1 p-6 md:p-8 flex flex-col justify-between gap-6">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary" className="rounded-lg font-bold px-2.5 py-0.5 uppercase tracking-widest text-[9px]">
                {task.format_label || task.format_id || "智能分析"}
              </Badge>
              <Badge className="rounded-lg px-2.5 py-0.5 font-bold text-[9px] uppercase tracking-widest bg-purple-500/10 text-purple-600 hover:bg-purple-500/20 border-none flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5 animate-spin" /> DeepSeek V3 驱动
              </Badge>
            </div>
            
            <h1 className="text-2xl md:text-3xl font-black leading-tight tracking-tight text-slate-855 dark:text-slate-100">
              {task.title || "未命名处理任务"}
            </h1>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-slate-100 dark:border-slate-800/80 text-xs font-bold text-muted-foreground">
            <div className="flex items-center gap-6">
              {task.duration_seconds && (
                <span className="flex items-center gap-1.5">
                  <Clock className="w-4 h-4" /> 
                  {Math.floor(task.duration_seconds / 60)}:{(task.duration_seconds % 60).toString().padStart(2, '0')}
                </span>
              )}
              <span className="flex items-center gap-1.5">
                创建于: {new Date(task.created_at).toLocaleDateString("zh-CN", {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit"
                })}
              </span>
            </div>

            <div className="flex items-center gap-3">
              <a 
                href={task.source_url} 
                target="_blank" 
                rel="noreferrer" 
                className="flex items-center gap-1 text-primary hover:underline hover:text-primary/80"
              >
                源视频链接 <ExternalLink className="w-3.5 h-3.5" />
              </a>
              {task.state === "succeeded" && (
                <Button 
                  variant="secondary" 
                  size="sm" 
                  className="rounded-xl font-bold h-8 text-[10px] gap-1.5 bg-blue-500/10 text-blue-600 hover:bg-blue-500 hover:text-white transition-all"
                  onClick={onDownloadVideo}
                >
                  <Download className="w-3.5 h-3.5" /> 下载视频
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};
