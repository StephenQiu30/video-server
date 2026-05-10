import React, { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Zap, Shield, Cpu, Layout } from "lucide-react";

gsap.registerPlugin(ScrollTrigger);

const features = [
  {
    name: "Lightning Fast Parsing",
    description: "Our distributed engine extracts high-quality video links in milliseconds.",
    icon: Zap,
    color: "text-yellow-500",
  },
  {
    name: "4K Resolution Support",
    description: "Choose your preferred quality manually, from mobile-friendly to crystal clear 4K.",
    icon: Layout,
    color: "text-blue-500",
  },
  {
    name: "AI Analysis (Beta)",
    description: "Get automated summaries, mind maps, and sentiment analysis for any video.",
    icon: Cpu,
    color: "text-purple-500",
  },
  {
    name: "Enterprise Security",
    description: "Your downloads and data are protected with bank-grade encryption.",
    icon: Shield,
    color: "text-green-500",
  },
];

const Features: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const cards = gsap.utils.toArray(".feature-card");
    
    gsap.fromTo(
      cards,
      { y: 60, opacity: 0 },
      {
        y: 0,
        opacity: 1,
        duration: 0.8,
        stagger: 0.2,
        scrollTrigger: {
          trigger: containerRef.current,
          start: "top 80%",
        },
      }
    );
  }, []);

  return (
    <div className="bg-background py-24 sm:py-32" ref={containerRef}>
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl lg:text-center">
          <h2 className="text-base font-semibold leading-7 text-primary">Everything you need</h2>
          <p className="mt-2 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            Designed for Creators and Developers
          </p>
          <p className="mt-6 text-lg leading-8 text-muted-foreground">
            A comprehensive suite of tools to manage your video workspace with unparalleled speed and precision.
          </p>
        </div>
        <div className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none">
          <dl className="grid max-w-xl grid-cols-1 gap-x-8 gap-y-16 lg:max-w-none lg:grid-cols-4">
            {features.map((feature) => (
              <div key={feature.name} className="feature-card flex flex-col items-start p-8 rounded-2xl bg-card border border-border hover:shadow-xl transition-shadow group">
                <div className={`rounded-lg bg-background p-3 ring-1 ring-border group-hover:ring-primary transition-all`}>
                  <feature.icon className={`h-6 w-6 ${feature.color}`} aria-hidden="true" />
                </div>
                <dt className="mt-4 font-semibold text-foreground">{feature.name}</dt>
                <dd className="mt-2 leading-7 text-muted-foreground">{feature.description}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </div>
  );
};

export default Features;
