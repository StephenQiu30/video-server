import React, { useState } from "react";
import { Sparkles, Clock, FileText, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface TaskActionsProps {
  summary: string;
  onExportPDF: () => void;
}

export const TaskActions: React.FC<TaskActionsProps> = ({ summary, onExportPDF }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(summary);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy", err);
    }
  };

  return (
    <div className="flex flex-col md:flex-row justify-between items-center gap-8 py-8 border-t border-slate-200/50 dark:border-slate-800/80 mt-12 bg-slate-50/50 dark:bg-slate-950/20 px-8 rounded-[2rem] border border-slate-100 dark:border-slate-800/50">
      <div className="flex items-center gap-8 text-[10px] font-black uppercase tracking-widest text-muted-foreground">
        <span className="flex items-center gap-2"><Sparkles className="w-4 h-4 text-purple-500 animate-pulse" /> DeepSeek V3</span>
        <span className="flex items-center gap-2"><Clock className="w-4 h-4 text-blue-500" /> 超速处理完成</span>
      </div>
      
      <div className="flex flex-wrap gap-4 w-full md:w-auto justify-end">
        <Button 
          variant="outline" 
          className="flex-1 md:flex-none h-12 px-8 rounded-xl font-bold border-slate-200/80 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800"
          onClick={onExportPDF}
        >
          <FileText className="w-4 h-4 mr-2 text-primary" /> 导出 PDF
        </Button>
        <Button 
          onClick={handleCopy}
          className="flex-1 md:flex-none h-12 px-10 rounded-xl font-black shadow-lg shadow-primary/20 bg-primary text-primary-foreground hover:bg-primary/90 transition-all flex items-center justify-center gap-2"
        >
          {copied ? (
            <>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" /> 已复制
            </>
          ) : (
            <>
              复制成果
            </>
          )}
        </Button>
      </div>
    </div>
  );
};
