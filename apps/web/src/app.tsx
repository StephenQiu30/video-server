import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import Workbench from "./pages/Workbench";
import Auth from "./pages/Auth";
import { Video } from "lucide-react";

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background font-sans antialiased">
        {/* Navigation Header */}
        <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="container mx-auto flex h-16 items-center justify-between px-4">
            <Link to="/" className="flex items-center space-x-2 group">
              <div className="bg-primary rounded-lg p-1.5 transition-transform group-hover:rotate-12">
                <Video className="h-5 w-5 text-primary-foreground" />
              </div>
              <span className="text-xl font-bold tracking-tight">StephenVideo</span>
            </Link>
            
            <nav className="hidden md:flex items-center space-x-6 text-sm font-medium">
              <Link to="/" className="transition-colors hover:text-primary">Home</Link>
              <Link to="/workbench" className="transition-colors hover:text-primary">Workbench</Link>
              <a href="#features" className="transition-colors hover:text-primary">Features</a>
              <a href="#pricing" className="transition-colors hover:text-primary text-muted-foreground">Pricing</a>
            </nav>

            <div className="flex items-center space-x-4">
              <Link to="/auth" className="text-sm font-medium hover:text-primary transition-colors">Login</Link>
              <Link to="/workbench" className="rounded-full bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-all shadow-md">
                Get Started
              </Link>
            </div>
          </div>
        </header>

        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/workbench" element={<Workbench />} />
          <Route path="/auth" element={<Auth />} />
          {/* Fallback */}
          <Route path="*" element={<LandingPage />} />
        </Routes>

        {/* Global Footer */}
        <footer className="border-t border-border bg-slate-50 dark:bg-slate-900/50 py-12">
          <div className="container mx-auto px-4 text-center">
            <p className="text-sm text-muted-foreground">
              © 2024 StephenVideo. Built with React + Shadcn UI + GSAP.
            </p>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
