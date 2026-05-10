## Context

The current frontend is built with Umi 4 and Ant Design Pro. While functional for management consoles, it lacks the "wow factor" and customizability required for a premium consumer SaaS. The user has requested a complete redesign using a modern React stack with Shadcn UI and Radix UI.

## Goals / Non-Goals

**Goals:**
- **Visual Excellence**: Achieve a premium, state-of-the-art look using Inter/Outfit fonts, smooth gradients, and glassmorphism.
- **Modern Stack**: Migrate to Vite + React + Tailwind CSS + Shadcn UI + GSAP.
- **Interactive Workbench**: A multi-step task creation flow: URL Input -> Fetch Info/Resolutions -> Select Resolution -> Create Task.
- **AI Hooks**: Visual integration of AI-powered analysis tools (Summary, Mindmap, Comments) as pre-designed placeholders.
- **Responsive Design**: Mobile-first approach for all pages.

**Non-Goals:**
- Backend implementation of AI features (UI-only for this phase).
- Multi-language support (English/Chinese only).
- Complex state management (Zustand or React Context will suffice).

## Decisions

- **Vite over Next.js**: Vite provides a faster development cycle and simpler deployment for a workbench-centric SPA. Since SEO is primarily needed for the landing page, we can optimize with static generation or simply keep it as part of the SPA for now.
- **Tailwind CSS + Shadcn UI**: This combination offers the best balance of speed and customizability, avoiding the "generic" look of component libraries like AntD.
- **GSAP**: Used for high-performance micro-animations, scroll-triggered effects, and complex timeline-based transitions in the landing page.
- **Lucide React**: Standardized, clean icon set.

## Risks / Trade-offs

- **[Risk] Complete Rewrite Delay**: A full rewrite is risky for timelines. 
  - **[Mitigation]**: Focus on the core path (Landing -> Login -> Download) first. Use Shadcn blocks to accelerate development.
- **[Risk] State Complexity**: The multi-step workbench could become complex.
  - **[Mitigation]**: Use a state machine or simple state management (Zustand) to manage the task creation wizard.
- **[Risk] API Integration**: New UI might require changes in how data is presented.
  - **[Mitigation]**: Reuse existing `/api/parse` and `/api/tasks` endpoints, mapping the new UI state to existing schemas.
