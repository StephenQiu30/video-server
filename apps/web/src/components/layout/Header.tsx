import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Video, Menu, X, LogOut } from "lucide-react";
import { siteConfig } from "@/config/site";
import { ThemeToggle } from "@/components/ThemeToggle";
import { UserDropdown } from "./UserDropdown";

interface User {
  id: number;
  email: string;
  avatar_url: string | null;
  display_name: string | null;
}

interface HeaderProps {
  user: User | null;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({ user, onLogout }) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8 w-full">
        <Link to="/" className="flex items-center space-x-2 group">
          <div className="bg-primary rounded-lg p-1.5 transition-transform group-hover:rotate-12">
            <Video className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="text-xl font-bold tracking-tight">{siteConfig.name}</span>
        </Link>
        
        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center space-x-6 text-sm font-medium">
          <Link to="/" className="transition-colors hover:text-primary">首页</Link>
          <Link to="/workbench" className="transition-colors hover:text-primary">工作台</Link>
          <a href="#features" className="transition-colors hover:text-primary">功能特性</a>
          <a href="#pricing" className="transition-colors hover:text-primary text-muted-foreground">价格计划</a>
        </nav>

        <div className="flex items-center space-x-3">
          <ThemeToggle />
          
          {/* User Account Section */}
          {user ? (
            <UserDropdown user={user} onLogout={onLogout} />
          ) : (
            <div className="hidden md:flex items-center space-x-4">
              <Link to="/auth" className="text-sm font-medium hover:text-primary transition-colors">登录</Link>
              <Link to="/workbench" className="rounded-full bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-all shadow-md">
                立即开始
              </Link>
            </div>
          )}

          {/* Mobile Menu Toggle */}
          <button 
            className="md:hidden p-2 rounded-md hover:bg-muted"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Overlay */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-border bg-background animate-in slide-in-from-top-4 duration-200">
          <nav className="flex flex-col p-4 space-y-4 text-sm font-medium">
            <Link to="/" onClick={() => setIsMobileMenuOpen(false)} className="px-2 py-1 hover:text-primary transition-colors">首页</Link>
            <Link to="/workbench" onClick={() => setIsMobileMenuOpen(false)} className="px-2 py-1 hover:text-primary transition-colors">工作台</Link>
            <a href="#features" onClick={() => setIsMobileMenuOpen(false)} className="px-2 py-1 hover:text-primary transition-colors">功能特性</a>
            
            {user ? (
              <>
                <div className="px-2 py-3 border-t border-slate-100 dark:border-slate-800 flex items-center gap-3.5 mt-2">
                  {user.avatar_url ? (
                    <img src={user.avatar_url} alt={user.display_name || "用户"} className="w-9 h-9 rounded-full shadow-sm border border-slate-200/20 object-cover" />
                  ) : (
                    <div className="w-9 h-9 rounded-full bg-primary/10 text-primary flex items-center justify-center font-black text-sm shadow-sm">
                      {(user.display_name || user.email || "?").charAt(0).toUpperCase()}
                    </div>
                  )}
                  <div className="truncate">
                    <p className="text-sm font-black tracking-tight text-slate-850 dark:text-slate-200 truncate">{user.display_name || "用户"}</p>
                    <p className="text-xs text-muted-foreground truncate mt-0.5">{user.email}</p>
                  </div>
                </div>
                <button 
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    onLogout();
                  }}
                  className="flex w-full items-center gap-2 px-2 py-2 text-sm font-bold text-red-600 hover:bg-red-500/10 rounded-xl transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  退出登录
                </button>
              </>
            ) : (
              <>
                <Link to="/auth" onClick={() => setIsMobileMenuOpen(false)} className="px-2 py-1 hover:text-primary transition-colors">登录</Link>
                <Link 
                  to="/workbench" 
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="inline-block w-full text-center rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground"
                >
                  立即开始
                </Link>
              </>
            )}
          </nav>
        </div>
      )}
    </header>
  );
};
