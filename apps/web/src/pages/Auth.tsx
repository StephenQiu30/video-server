import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, GitBranch, Loader2, ShieldCheck, UserCircle2 } from "lucide-react";
import { siteConfig } from "../config/site";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";

const Auth: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [isRedirecting, setIsRedirecting] = useState(false);
  const isCallback = Boolean(searchParams.get("code"));
  const isLoading = isRedirecting || isCallback;

  const handleGitHubLogin = () => {
    setIsRedirecting(true);
    window.location.href = `${siteConfig.apiBaseUrl}/auth/github/authorize`;
  };

  useEffect(() => {
    const token = searchParams.get("token");
    if (token) {
      localStorage.setItem("auth_token", token);
      navigate("/workbench");
      return;
    }

    const code = searchParams.get("code");
    if (code) {
      window.location.href = `${siteConfig.apiBaseUrl}/auth/github/callback?code=${code}`;
      return;
    }
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen bg-[#eef6ff] flex items-center justify-center px-4 py-10">
      <Card className="w-full max-w-md border-slate-200/80 bg-white/95 p-2 shadow-sm">
        <CardHeader className="space-y-5 pb-4">
          <div className="inline-flex items-center justify-between gap-2 text-xs uppercase tracking-[0.16em] text-slate-500">
            <span className="inline-flex items-center gap-1 rounded-full bg-sky-50 px-3 py-1 text-[10px]">
              <ShieldCheck className="h-3.5 w-3.5 text-sky-600" />
              登录信息中心
            </span>
            <span className="rounded-full border border-slate-200 px-2 py-1">v1.0</span>
          </div>
          <div className="text-center">
            <CardTitle className="text-3xl font-semibold text-slate-900">
              {isLoading ? "授权中" : "登录系统"}
            </CardTitle>
            <CardDescription className="mt-3 text-sm text-slate-600">
              {isLoading
                ? "OAuth 流程进行中，请保持页面不关闭"
                : "安全、统一的方式接入 GitHub，进入你的工作区。"}
            </CardDescription>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          <div className="grid gap-2">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-[0.14em] text-slate-500">当前登录信息</p>
              <div className="mt-2 flex items-center gap-3">
                <UserCircle2 className="h-9 w-9 text-slate-500" />
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-900">GitHub 统一授权</p>
                  <p className="truncate text-xs text-slate-500">成功授权后可直接使用工作台与任务管理。</p>
                </div>
              </div>
            </div>
            <div className="rounded-2xl border border-sky-100 bg-sky-50 p-4">
              <p className="text-xs uppercase tracking-[0.14em] text-sky-600">已支持项</p>
              <p className="mt-2 text-sm text-slate-700">解析视频、任务进度、AI 洞察、下载归档。</p>
            </div>
          </div>

          <Button 
            onClick={handleGitHubLogin}
            disabled={isLoading}
            className="w-full h-12 rounded-full bg-slate-900/90 hover:bg-slate-900 text-white"
          >
            {isLoading ? (
              <Loader2 className="w-6 h-6 animate-spin" />
            ) : (
              <>
                <GitBranch className="w-6 h-6 mr-3" />
                使用 GitHub 账号登录
              </>
            )}
          </Button>
        </CardContent>

        <CardFooter className="flex flex-col gap-4">
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3">
            <p className="text-xs font-medium text-emerald-800">状态：{isLoading ? "认证中" : "未登录"}</p>
            <p className="mt-1 text-[11px] text-emerald-700">OAuth 与账号资料处理遵循最小权限读取策略。</p>
          </div>
          <p className="text-center text-xs text-slate-500">
            由 GitHub OAuth 2.0 提供安全授权
          </p>
          <Link
            to="/"
            className="inline-flex items-center justify-center gap-2 text-sm font-semibold text-slate-700 hover:text-sky-700"
          >
            <ArrowLeft className="w-4 h-4" />
            返回首页
          </Link>
        </CardFooter>
      </Card>
    </div>
  );
};

export default Auth;
