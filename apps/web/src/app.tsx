import React from "react";
import { BrowserRouter as Router, Routes, Route, useLocation, useNavigate } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import Workbench from "./pages/Workbench";
import TaskDetail from "./pages/TaskDetail";
import Auth from "./pages/Auth";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { ThemeProvider } from "./components/ThemeProvider";
import { api } from "./lib/api";
import { siteConfig } from "./config/site";
import { Header } from "./components/layout/Header";

const queryClient = new QueryClient();



function AppContent() {
  const location = useLocation();
  const navigate = useNavigate();



  const token = localStorage.getItem("auth_token");

  const { data: user, refetch } = useQuery({
    queryKey: ["currentUser", token],
    queryFn: async () => {
      if (!token) return null;
      try {
        const res = await api.get("/auth/me");
        return res.data;
      } catch (err) {
        console.error("Failed to fetch user:", err);
        return null;
      }
    },
    enabled: !!token,
  });

  // Re-fetch user if token is set/cleared or on navigation changes
  React.useEffect(() => {
    if (token) {
      refetch();
    }
  }, [token, location.pathname, refetch]);

  const handleLogout = () => {
    localStorage.removeItem("auth_token");
    queryClient.setQueryData(["currentUser", token], null);
    navigate("/");
    window.location.reload();
  };

  return (
    <div className="min-h-screen bg-background font-sans antialiased text-foreground">
      {/* Decoupled Layout Navigation Header */}
      <Header user={user} onLogout={handleLogout} />

      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/workbench" element={<Workbench />} />
        <Route path="/workbench/task/:id" element={<TaskDetail />} />
        <Route path="/auth" element={<Auth />} />
        <Route path="/api/auth/github/callback" element={<Auth />} />
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
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="light" storageKey="video-ui-theme">
        <Router>
          <AppContent />
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
