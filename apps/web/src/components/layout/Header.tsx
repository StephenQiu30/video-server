import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Menu, X, LogOut, Sparkles } from "lucide-react";
import { siteConfig } from "@/config/site";
import { ThemeToggle } from "@/components/ThemeToggle";

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

  const navItems = [
    { label: "首页", href: "/" },
    { label: "功能", href: "#features" },
    { label: "社会证明", href: "#proof" },
    { label: "价格", href: "#pricing" },
    { label: "FAQ", href: "#faq" },
  ];

  return (
    <header className="sticky top-4 z-50 w-[calc(100%-2rem)] sm:w-[calc(100%-3rem)] left-0 right-0 mx-auto rounded-full border border-white/80 bg-white/80 px-3 py-2 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-white/90">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between">
        <Link to="/" className="flex items-center space-x-2 group">
          <div className="inline-flex items-center justify-center rounded-full bg-sky-500 p-1.5 text-white transition-transform group-hover:rotate-6">
            <Sparkles className="h-4 w-4" />
          </div>
          <span className="text-xl font-bold tracking-tight text-slate-900">{siteConfig.name}</span>
        </Link>

        <nav className="hidden md:flex items-center text-sm font-medium">
          {navItems.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="rounded-full px-4 py-2 text-slate-700 transition hover:bg-sky-50 hover:text-sky-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-200"
            >
              {item.label}
            </a>
          ))}
          <Link
            to="/workbench"
            className="rounded-full px-4 py-2 text-slate-700 transition hover:bg-sky-50 hover:text-sky-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-200"
          >
            工作台
          </Link>
        </nav>

        <div className="flex items-center space-x-3">
          <ThemeToggle />

          {user ? (
            <div className="hidden md:flex items-center space-x-4">
              <Link to="/auth" className="text-sm font-medium text-slate-700 transition-colors hover:text-sky-700">
                登录
              </Link>
              <Link
                to="/workbench"
                className="min-h-[40px] rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-sky-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300"
              >
                立即开始
              </Link>
            </div>
          ) : (
            <div className="hidden md:flex items-center space-x-4">
              <Link to="/auth" className="text-sm font-medium text-slate-700 transition-colors hover:text-sky-700">
                登录
              </Link>
              <Link
                to="/workbench"
                className="min-h-[40px] rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-sky-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300"
              >
                立即开始
              </Link>
            </div>
          )}

        <button
            type="button"
            className="md:hidden inline-flex h-10 min-h-[40px] min-w-[40px] items-center justify-center rounded-full text-slate-700 transition hover:bg-sky-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-label={isMobileMenuOpen ? "close menu" : "open menu"}
            aria-expanded={isMobileMenuOpen}
          >
            {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {isMobileMenuOpen && (
        <div className="md:hidden mt-2 rounded-3xl border border-sky-100 bg-white p-3 shadow-lg">
          <nav className="flex flex-col p-4 space-y-3 text-sm font-medium">
            {navItems.map((item) => (
              <a
                key={item.label}
                href={item.href}
                onClick={() => setIsMobileMenuOpen(false)}
                className="rounded-2xl px-3 py-2 text-slate-700 hover:bg-sky-50 hover:text-sky-700"
              >
                {item.label}
              </a>
            ))}
            <Link
              to="/workbench"
              onClick={() => setIsMobileMenuOpen(false)}
              className="rounded-2xl px-3 py-2 text-slate-700 hover:bg-sky-50 hover:text-sky-700"
            >
              工作台
            </Link>

            {user ? (
              <>
                <div className="rounded-2xl px-3 py-3 border-t border-sky-100 flex items-center gap-3.5 mt-2">
                  {user.avatar_url ? (
                    <img
                      src={user.avatar_url}
                      alt={user.display_name || "用户"}
                      className="w-9 h-9 rounded-full shadow-sm border border-slate-200/20 object-cover"
                    />
                  ) : (
                    <div className="w-9 h-9 rounded-full bg-sky-100 text-sky-700 flex items-center justify-center font-black text-sm shadow-sm">
                      {(user.display_name || user.email || "?").charAt(0).toUpperCase()}
                    </div>
                  )}
                  <div className="truncate">
                    <p className="text-sm font-black tracking-tight text-slate-850 truncate">{user.display_name || "用户"}</p>
                    <p className="text-xs text-slate-500 truncate mt-0.5">{user.email}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    onLogout();
                  }}
                  aria-label="退出登录"
                  className="flex w-full items-center gap-2 px-2 py-2 text-sm font-bold text-red-600 hover:bg-red-500/10 rounded-xl transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  退出登录
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/auth"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="rounded-2xl px-3 py-2 text-slate-700 hover:bg-sky-50 hover:text-sky-700"
                >
                  登录
                </Link>
                <Link
                  to="/workbench"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="rounded-2xl px-3 py-2 text-center bg-sky-500 text-white hover:bg-sky-600"
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
