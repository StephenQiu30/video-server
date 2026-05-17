import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Video, Code as Github, Loader2, AlertCircle, ArrowRight } from "lucide-react";
import { siteConfig } from "../config/site";
import { api } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

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
    // 1. Check if we have a token from a direct backend redirect
    const token = searchParams.get("token");
    if (token) {
      localStorage.setItem("auth_token", token);
      navigate("/workbench");
      return;
    }

    // 2. Check if we have a code and need to exchange it
    const code = searchParams.get("code");
    if (code) {
      window.location.href = `${siteConfig.apiBaseUrl}/auth/github/callback?code=${code}`;
      return;
    }
  }, [searchParams, handleCallback, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 px-4">
      <Card className="max-w-md w-full border-none shadow-2xl rounded-3xl p-6 md:p-8 animate-in fade-in zoom-in duration-500">
        <CardHeader className="text-center space-y-4">
          <div className="inline-flex items-center justify-center p-4 bg-primary rounded-2xl mx-auto shadow-lg shadow-primary/20">
            <Video className="w-8 h-8 text-primary-foreground" />
          </div>
          <CardTitle className="text-3xl font-black tracking-tight">
            {status === "loading" ? "身份验证中..." : "欢迎回归"}
          </CardTitle>
          <CardDescription className="text-base">
            {status === "loading" 
              ? "请稍候，我们正在与 GitHub 建立安全连接" 
              : "一键开启您的智能视频处理之旅"}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {status === "error" && (
            <Alert variant="destructive" className="rounded-2xl">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="font-medium">{errorMsg}</AlertDescription>
            </Alert>
          )}

          <Button 
            onClick={handleGitHubLogin}
            disabled={status === "loading"}
            className="w-full h-14 rounded-2xl text-lg font-bold shadow-lg shadow-primary/20"
          >
            {status === "loading" ? (
              <Loader2 className="w-6 h-6 animate-spin" />
            ) : (
              <>
                <Github className="w-6 h-6 mr-3" />
                使用 GitHub 账号登录
              </>
            )}
          </Button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase tracking-widest text-muted-foreground">
              <span className="bg-card px-2">Secure Access</span>
            </div>
          </div>
        </CardContent>

        <CardFooter className="flex flex-col gap-4">
          <p className="text-center text-xs text-muted-foreground opacity-60">
            由 GitHub OAuth 2.0 提供安全认证支持
          </p>
          <Link to="/" className="text-sm font-bold text-primary hover:underline flex items-center justify-center gap-2">
            返回首页 <ArrowRight className="w-4 h-4" />
          </Link>
        </CardFooter>
      </Card>
    </div>
  );
};

export default Auth;
