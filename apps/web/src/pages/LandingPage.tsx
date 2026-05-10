import React from "react";
import Hero from "../components/Hero";
import Features from "../components/Features";

const LandingPage: React.FC = () => {
  return (
    <main className="min-h-screen">
      <Hero />
      <Features />
      
      {/* Visual divider */}
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="h-px bg-gradient-to-r from-transparent via-border to-transparent" />
      </div>
      
      {/* Footer-like CTA */}
      <section className="py-24 text-center">
        <h3 className="text-2xl font-bold">Ready to revolutionize your workflow?</h3>
        <p className="text-muted-foreground mt-4 max-w-md mx-auto">
          Join thousands of users who trust us for their video downloading needs.
        </p>
        <button className="mt-8 rounded-full bg-primary px-8 py-3 font-semibold text-primary-foreground hover:bg-primary/90 transition-all">
          Get Started for Free
        </button>
      </section>
    </main>
  );
};

export default LandingPage;
