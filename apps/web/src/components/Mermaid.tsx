import React, { useEffect, useRef } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: true,
  theme: "neutral",
  securityLevel: "loose",
});

const Mermaid: React.FC<{ chart: string }> = ({ chart }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current && chart) {
      mermaid.contentLoaded();
      mermaid.render("mermaid-svg-" + Math.random().toString(36).substr(2, 9), chart).then(({ svg }) => {
        if (ref.current) {
          ref.current.innerHTML = svg;
        }
      });
    }
  }, [chart]);

  return <div ref={ref} className="mermaid flex justify-center py-4 bg-slate-50 dark:bg-slate-900/50 rounded-xl overflow-auto" />;
};

export default Mermaid;
