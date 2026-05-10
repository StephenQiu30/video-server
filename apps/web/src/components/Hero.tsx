import React, { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ArrowRight, Play } from "lucide-react";

const Hero: React.FC = () => {
  const heroRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const subRef = useRef<HTMLParagraphElement>(null);
  const btnRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
    
    tl.fromTo(
      titleRef.current,
      { y: 50, opacity: 0 },
      { y: 0, opacity: 1, duration: 1, delay: 0.2 }
    )
    .fromTo(
      subRef.current,
      { y: 30, opacity: 0 },
      { y: 0, opacity: 1, duration: 1 },
      "-=0.6"
    )
    .fromTo(
      btnRef.current,
      { scale: 0.9, opacity: 0 },
      { scale: 1, opacity: 1, duration: 0.8 },
      "-=0.6"
    );
  }, []);

  return (
    <div ref={heroRef} className="relative isolate overflow-hidden bg-background pt-14">
      <div className="mx-auto max-w-7xl px-6 py-24 sm:py-32 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h1
            ref={titleRef}
            className="text-4xl font-bold tracking-tight text-foreground sm:text-6xl bg-clip-text text-transparent bg-gradient-to-r from-primary to-blue-600"
          >
            Experience Video Downloads Like Never Before
          </h1>
          <p ref={subRef} className="mt-6 text-lg leading-8 text-muted-foreground">
            The ultimate SaaS platform for high-speed video parsing and downloading. 
            Select resolutions up to 4K, analyze content with AI, and manage your library with ease.
          </p>
          <div ref={btnRef} className="mt-10 flex items-center justify-center gap-x-6">
            <button className="rounded-full bg-primary px-8 py-4 text-sm font-semibold text-primary-foreground shadow-lg hover:bg-primary/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary flex items-center gap-2 group transition-all">
              Start Building Now
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
            <button className="text-sm font-semibold leading-6 text-foreground flex items-center gap-2 hover:text-primary transition-colors">
              Watch Demo <Play className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
      
      {/* Decorative background element */}
      <div className="absolute inset-x-0 -top-40 -z-10 transform-gpu overflow-hidden blur-3xl sm:-top-80" aria-hidden="true">
        <div className="relative left-[calc(50%-11rem)] aspect-[1155/678] w-[36.125rem] -translate-x-1/2 rotate-[30deg] bg-gradient-to-tr from-[#ff80b5] to-[#9089fc] opacity-20 sm:left-[calc(50%-30rem)] sm:w-[72.1875rem]"></div>
      </div>
    </div>
  );
};

export default Hero;
