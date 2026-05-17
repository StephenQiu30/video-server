import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, LogOut, LayoutDashboard } from "lucide-react";
import { cn } from "@/lib/utils";

interface User {
  id: number;
  email: string;
  avatar_url: string | null;
  display_name: string | null;
}

interface UserDropdownProps {
  user: User;
  onLogout: () => void;
}

export const UserDropdown: React.FC<UserDropdownProps> = ({ user, onLogout }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setIsMenuOpen(!isMenuOpen)}
        className="flex items-center gap-2.5 p-1.5 rounded-full hover:bg-slate-100 dark:hover:bg-slate-805/80 transition-all border border-slate-200/60 dark:border-slate-800/80 focus:outline-none focus:ring-2 focus:ring-primary/20 bg-background/50 backdrop-blur-md"
      >
        {user.avatar_url ? (
          <img
            src={user.avatar_url}
            alt={user.display_name || "用户"}
            className="w-7 h-7 rounded-full object-cover shadow-sm border border-slate-200/20"
          />
        ) : (
          <div className="w-7 h-7 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs shadow-sm">
            {(user.display_name || user.email || "?").charAt(0).toUpperCase()}
          </div>
        )}
        <span className="hidden lg:inline text-xs font-black tracking-tight px-1 max-w-[100px] truncate">
          {user.display_name || "我的账号"}
        </span>
        <ChevronDown className={cn("w-3.5 h-3.5 opacity-60 transition-transform duration-200 mr-1", isMenuOpen && "rotate-180")} />
      </button>

      {isMenuOpen && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-30" onClick={() => setIsMenuOpen(false)} />
          {/* Dropdown Card */}
          <div className="absolute right-0 mt-3 w-64 rounded-[1.5rem] border border-slate-200/85 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl p-2.5 shadow-2xl shadow-slate-900/10 dark:shadow-black/50 z-40 animate-in fade-in slide-in-from-top-3 duration-300">
            <div className="px-3.5 py-3 border-b border-slate-100 dark:border-slate-800/80">
              <p className="text-sm font-black tracking-tight truncate text-slate-800 dark:text-slate-200">
                {user.display_name || "用户"}
              </p>
              <p className="text-xs text-muted-foreground truncate font-medium mt-0.5">
                {user.email}
              </p>
            </div>
            <div className="py-2 space-y-0.5">
              <Link
                to="/workbench"
                onClick={() => setIsMenuOpen(false)}
                className="flex w-full items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-sm font-bold hover:bg-slate-50 dark:hover:bg-slate-800/50 text-slate-700 dark:text-slate-300 transition-colors"
              >
                <LayoutDashboard className="w-4 h-4 text-primary" />
                工作台
              </Link>
              <button
                onClick={() => {
                  setIsMenuOpen(false);
                  onLogout();
                }}
                className="flex w-full items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-sm font-bold text-red-600 hover:bg-red-500/10 dark:text-red-400 dark:hover:bg-red-500/15 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                退出登录
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
