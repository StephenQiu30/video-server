import React, { useState } from "react";
import { Search, List, BarChart3, Settings, Brain, MessageSquare, Map, Download, CheckCircle2, Clock } from "lucide-react";
import { cn } from "../lib/utils";

const Workbench: React.FC = () => {
  const [url, setUrl] = useState("");
  const [step, setStep] = useState(1); // 1: Input, 2: Selection
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleAnalyze = () => {
    setIsAnalyzing(true);
    setTimeout(() => {
      setIsAnalyzing(false);
      setStep(2);
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 md:p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Creator Workbench</h1>
            <p className="text-muted-foreground mt-1">Manage your video processing pipeline with ease.</p>
          </div>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-card hover:bg-muted transition-all">
              <Settings className="w-4 h-4" /> Settings
            </button>
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-md">
              Upgrade to Pro
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Control Panel */}
          <div className="lg:col-span-2 space-y-6">
            <div className="p-6 rounded-2xl border border-border bg-card shadow-sm backdrop-blur-xl bg-white/50 dark:bg-black/50">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Search className="w-5 h-5 text-primary" /> New Task
              </h2>
              <div className="space-y-4">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Paste video URL (YouTube, Bilibili, TikTok...)"
                    className="w-full px-4 py-4 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary outline-none transition-all pr-32"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                  />
                  <button 
                    onClick={handleAnalyze}
                    disabled={!url || isAnalyzing}
                    className="absolute right-2 top-2 bottom-2 px-6 rounded-lg bg-primary text-primary-foreground font-medium disabled:opacity-50 transition-all"
                  >
                    {isAnalyzing ? "Analyzing..." : "Analyze"}
                  </button>
                </div>

                {step === 2 && (
                  <div className="animate-in fade-in slide-in-from-top-4 duration-500 space-y-6 pt-4 border-t border-border">
                    <div className="flex gap-4">
                      <div className="w-32 h-20 rounded-lg bg-muted flex-shrink-0 overflow-hidden relative group">
                        <img src="https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&q=80&w=200" alt="Thumbnail" className="w-full h-full object-cover group-hover:scale-110 transition-transform" />
                        <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
                          <Clock className="w-4 h-4 text-white" />
                        </div>
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg line-clamp-1">How to build a SaaS in 24 hours</h3>
                        <p className="text-sm text-muted-foreground mt-1">Source: YouTube • Duration: 15:24</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {['4K (2160p)', '1080p Full HD', '720p HD', 'MP3 Audio Only'].map((res, i) => (
                        <button key={res} className={cn(
                          "px-4 py-3 rounded-xl border border-border text-sm font-medium transition-all text-left group hover:border-primary",
                          i === 1 ? "border-primary bg-primary/5" : "bg-card"
                        )}>
                          <div className="text-xs text-muted-foreground mb-1 group-hover:text-primary/70">Resolution</div>
                          <div>{res}</div>
                        </button>
                      ))}
                    </div>

                    <button className="w-full py-4 rounded-xl bg-primary text-primary-foreground font-bold shadow-lg hover:shadow-primary/20 transition-all flex items-center justify-center gap-2">
                      <Download className="w-5 h-5" /> Initialize Download Task
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Recent Tasks */}
            <div className="p-6 rounded-2xl border border-border bg-card shadow-sm">
               <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <List className="w-5 h-5 text-primary" /> Active Tasks
              </h2>
              <div className="space-y-4">
                {[
                  { name: "Modern Web Design 2024", progress: 65, size: "1.2 GB", status: "Downloading" },
                  { name: "AI Revolution Explained", progress: 100, size: "450 MB", status: "Completed" },
                ].map((task) => (
                  <div key={task.name} className="p-4 rounded-xl border border-border hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors">
                    <div className="flex justify-between items-center mb-3">
                      <span className="font-medium">{task.name}</span>
                      <span className={cn(
                        "text-xs px-2 py-1 rounded-full flex items-center gap-1",
                        task.status === "Completed" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                      )}>
                        {task.status === "Completed" ? <CheckCircle2 className="w-3 h-3" /> : <Clock className="w-3 h-3 animate-spin" />}
                        {task.status}
                      </span>
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
                <Brain className="w-5 h-5 text-purple-500" /> AI Video Tools
              </h2>
              <div className="space-y-3">
                {[
                  { name: "AI Summary", icon: MessageSquare, desc: "Get a concise summary of video content.", beta: false },
                  { name: "Mind Map", icon: Map, desc: "Generate visual structure of key ideas.", beta: true },
                  { name: "Comment Analysis", icon: BarChart3, desc: "Understand audience sentiment instantly.", beta: true },
                ].map((tool) => (
                  <button key={tool.name} className="w-full text-left p-4 rounded-xl border border-border hover:bg-slate-50 dark:hover:bg-slate-900 transition-all group relative overflow-hidden">
                    <div className="flex items-center justify-between mb-1">
                      <tool.icon className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
                      {tool.beta && <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">BETA</span>}
                    </div>
                    <div className="font-semibold text-sm">{tool.name}</div>
                    <div className="text-xs text-muted-foreground mt-1">{tool.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-gradient-to-br from-primary to-blue-600 text-white shadow-lg">
               <h3 className="font-bold text-lg">Pro Feature</h3>
               <p className="text-white/80 text-sm mt-2">Unlock unlimited parallel downloads and prioritized processing.</p>
               <button className="w-full mt-4 py-2 rounded-lg bg-white text-primary font-bold text-sm">Upgrade Now</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Workbench;
