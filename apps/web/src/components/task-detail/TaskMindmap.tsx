import React from "react";
import { Map } from "lucide-react";
import Mermaid from "@/components/Mermaid";

interface TaskMindmapProps {
  mindmap: string;
}

export const TaskMindmap: React.FC<TaskMindmapProps> = ({ mindmap }) => {
  return (
    <section className="space-y-6">
      <h2 className="text-2xl font-black flex items-center gap-3 uppercase tracking-wider text-slate-850 dark:text-slate-100">
        <Map className="w-7 h-7 text-primary" /> 逻辑视觉地图
      </h2>
      <div className="p-6 md:p-10 rounded-[2.5rem] bg-white dark:bg-slate-900 border border-slate-200/50 dark:border-slate-800/80 shadow-sm overflow-hidden transition-all hover:shadow-md">
        <div className="w-full overflow-x-auto rounded-[1.5rem] py-4 bg-slate-50/50 dark:bg-slate-950/20 border border-slate-100 dark:border-slate-800/50 flex justify-center min-h-[300px]">
          <div className="min-w-[800px] px-8 flex justify-center items-center">
            <Mermaid chart={mindmap} />
          </div>
        </div>
      </div>
    </section>
  );
};
