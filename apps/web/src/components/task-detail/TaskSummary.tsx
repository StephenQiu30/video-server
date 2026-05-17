import React from "react";
import { FileText } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface TaskSummaryProps {
  summary: string;
}

export const TaskSummary: React.FC<TaskSummaryProps> = ({ summary }) => {
  return (
    <section className="space-y-6">
      <h2 className="text-2xl font-black flex items-center gap-3 uppercase tracking-wider text-slate-850 dark:text-slate-100">
        <FileText className="w-7 h-7 text-primary" /> 内容深度总结
      </h2>
      <div className="prose prose-lg prose-slate dark:prose-invert max-w-none p-8 md:p-12 rounded-[2.5rem] bg-white dark:bg-slate-900 border border-slate-200/50 dark:border-slate-800/80 leading-relaxed font-medium shadow-sm transition-all hover:shadow-md">
        <ReactMarkdown>{summary}</ReactMarkdown>
      </div>
    </section>
  );
};
