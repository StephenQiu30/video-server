import { useState } from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import Workbench from "./pages/Workbench";
import Auth from "./pages/Auth";
import { Video, Menu, X } from "lucide-react";
import { siteConfig } from "./config/site";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "./components/ThemeProvider";
import { ThemeToggle } from "./components/ThemeToggle";

const queryClient = new QueryClient();

function App() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="light" storageKey="video-ui-theme">
        <Router>
          <div className="min-h-screen bg-background font-sans antialiased text-foreground">
            {/* Navigation Header */}
            <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
              <div className="container mx-auto flex h-16 items-center justify-between px-4">
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

                <div className="flex items-center space-x-2">
                  <ThemeToggle />
                  <div className="hidden md:flex items-center space-x-4">
                    <Link to="/auth" className="text-sm font-medium hover:text-primary transition-colors">登录</Link>
                    <Link to="/workbench" className="rounded-full bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-all shadow-md">
                      立即开始
                    </Link>
                  </div>
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
                    <Link to="/auth" onClick={() => setIsMobileMenuOpen(false)} className="px-2 py-1 hover:text-primary transition-colors">登录</Link>
                    <Link 
                      to="/workbench" 
                      onClick={() => setIsMobileMenuOpen(false)}
                      className="inline-block w-full text-center rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground"
                    >
                      立即开始
                    </Link>
                  </nav>
                </div>
              )}
            </header>

            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/workbench" element={<Workbench />} />
              <Route path="/auth" element={<Auth />} />
              <Route path="/api/auth/github/callback" element={<Auth />} />
              {/* Fallback */}
              <Route path="*" element={<LandingPage />} />
            </Routes>

            {/* Global Footer */}
            <footer className="border-t border-border bg-slate-50 dark:bg-slate-900/50 py-12">
              <div className="container mx-auto px-4 text-center">
                <p className="text-sm text-muted-foreground">
                  © {siteConfig.currentYear} {siteConfig.name}. 使用 React + Tailwind CSS 构建。
                </p>
              </div>
            </footer>
          </div>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
