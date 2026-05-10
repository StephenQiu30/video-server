import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Video, Code as Github, Loader2, AlertCircle } from "lucide-react";
import { siteConfig } from "../config/site";
import { api } from "../lib/api";

const Auth: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleGitHubLogin = () => {
    window.location.href = `${siteConfig.apiBaseUrl}/auth/github/authorize`;
  };

  const handleCallback = React.useCallback(async (code: string) => {
    setStatus("loading");
    try {
      const response = await api.get(`/auth/github/callback?code=${code}`);
      const { access_token } = response.data;
      localStorage.setItem("auth_token", access_token);
      navigate("/workbench");
    } catch (err: unknown) {
      console.error("Auth failed:", err);
      setStatus("error");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setErrorMsg((err as any).response?.data?.detail || "认证失败，请稍后重试");
    }
  }, [navigate]);

  useEffect(() => {
    const code = searchParams.get("code");
    if (code) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      handleCallback(code);
    }
  }, [searchParams, handleCallback]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 px-4 relative overflow-hidden">
      {/* Decorative Background */}
      <div className="absolute top-0 left-0 w-full h-full -z-10 opacity-30">
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-primary/20 rounded-full blur-[150px] animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-blue-400/20 rounded-full blur-[150px] animate-pulse delay-1000" />
      </div>

      <div className="max-w-md w-full space-y-10 p-12 rounded-[3rem] glass-card relative overflow-hidden animate-in fade-in zoom-in duration-700">
        <div className="text-center space-y-6">
          <Link to="/" className="inline-flex items-center justify-center p-5 bg-primary rounded-[2rem] shadow-2xl shadow-primary/30 animate-float">
            <Video className="w-10 h-10 text-primary-foreground" />
          </Link>
          <div className="space-y-2">
            <h2 className="text-4xl font-black tracking-tight text-foreground">
              {status === "loading" ? "正在同步..." : "欢迎回归"}
            </h2>
            <p className="text-muted-foreground text-sm font-medium leading-relaxed">
              {status === "loading" 
                ? "请稍候，我们正在通过加密通道与 GitHub 建立连接" 
                : "一键开启您的智能视频处理之旅"}
            </p>
          </div>
        </div>

        <div className="space-y-8">
          {status === "error" && (
            <div className="p-5 rounded-2xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-start gap-4 animate-in slide-in-from-top-2 duration-300">
              <AlertCircle className="w-6 h-6 shrink-0" />
              <p className="font-semibold leading-relaxed">{errorMsg}</p>
            </div>
          )}

          <button 
            onClick={handleGitHubLogin}
            disabled={status === "loading"}
            className="w-full flex items-center justify-center gap-4 py-5 bg-slate-950 dark:bg-white dark:text-slate-950 text-white rounded-[1.5rem] font-black text-lg hover:shadow-[0_20px_50px_rgba(0,0,0,0.2)] hover:-translate-y-1 active:scale-95 transition-all disabled:opacity-50 group relative overflow-hidden"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite] transition-transform" />
            {status === "loading" ? (
              <Loader2 className="w-7 h-7 animate-spin" />
            ) : (
              <>
                <Github className="w-7 h-7" />
                使用 GitHub 登录
              </>
            )}
          </button>
          
          <div className="space-y-4">
             <div className="flex items-center gap-4 py-4 px-2">
                <div className="h-px flex-1 bg-border" />
                <span className="text-[10px] font-black uppercase tracking-[0.3em] text-muted-foreground opacity-50">Secure Access</span>
                <div className="h-px flex-1 bg-border" />
             </div>
             
             <div className="text-center">
                <Link to="/" className="text-xs font-bold text-muted-foreground hover:text-primary transition-all flex items-center justify-center gap-2 group">
                   返回控制台首页
                   <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
                </Link>
             </div>
          </div>
        </div>

        <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-primary via-blue-400 to-primary animate-[shimmer_3s_linear_infinite]" />
      </div>
    </div>
  );
};

export default Auth;
