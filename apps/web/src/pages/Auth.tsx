import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Video, Github, Loader2, AlertCircle } from "lucide-react";
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

  useEffect(() => {
    const code = searchParams.get("code");
    if (code) {
      handleCallback(code);
    }
  }, [searchParams]);

  const handleCallback = async (code: string) => {
    setStatus("loading");
    try {
      const response = await api.get(`/auth/github/callback?code=${code}`);
      const { access_token } = response.data;
      localStorage.setItem("auth_token", access_token);
      navigate("/workbench");
    } catch (err: any) {
      console.error("Auth failed:", err);
      setStatus("error");
      setErrorMsg(err.response?.data?.detail || "认证失败，请稍后重试");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 px-4">
      <div className="max-w-md w-full space-y-8 p-10 rounded-3xl bg-card border border-border shadow-2xl relative overflow-hidden">
        {/* Decoration */}
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary to-blue-600" />
        
        <div className="text-center">
          <Link to="/" className="inline-flex items-center justify-center p-3 bg-primary rounded-2xl mb-6 shadow-lg shadow-primary/20">
            <Video className="w-8 h-8 text-primary-foreground" />
          </Link>
          <h2 className="text-3xl font-bold tracking-tight text-foreground">
            {status === "loading" ? "正在认证..." : "欢迎回来"}
          </h2>
          <p className="text-muted-foreground mt-3 text-sm">
            {status === "loading" 
              ? "请稍候，我们正在与 GitHub 建立安全连接" 
              : "使用 GitHub 账号一键开启您的创作之旅"}
          </p>
        </div>

        <div className="pt-4">
          {status === "error" && (
            <div className="mb-6 p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <p>{errorMsg}</p>
            </div>
          )}

          <button 
            onClick={handleGitHubLogin}
            disabled={status === "loading"}
            className="w-full flex items-center justify-center gap-3 py-4 bg-slate-900 dark:bg-white dark:text-slate-900 text-white rounded-2xl font-bold text-lg hover:opacity-90 transition-all shadow-xl disabled:opacity-50 group"
          >
            {status === "loading" ? (
              <Loader2 className="w-6 h-6 animate-spin" />
            ) : (
              <>
                <Github className="w-6 h-6" />
                使用 GitHub 登录
              </>
            )}
          </button>
          
          <p className="text-center text-[11px] text-muted-foreground mt-8 leading-relaxed uppercase tracking-widest opacity-60">
            Securely powered by GitHub OAuth 2.0
          </p>
        </div>

        <div className="pt-6 text-center">
           <Link to="/" className="text-sm text-muted-foreground hover:text-primary transition-colors">
              返回首页
           </Link>
        </div>
      </div>
    </div>
  );
};

export default Auth;
