# Proposal: Shadcn UI Redesign

## Goal
Redesign the entire frontend using Shadcn UI components and follow the `uiuxpromax` principles. 
Key requirements:
1. No gradients.
2. Professional, clean, and high-performance design.
3. Full responsive support.
4. Use Shadcn UI for all major components (Button, Input, Card, etc.).

## Context
The current design uses custom glassmorphism and gradients which the user wants to replace with a more standardized and clean Shadcn UI aesthetic.

## Proposed Changes
1. Initialize Shadcn UI in `apps/web`.
2. Rewrite `index.css` to remove gradients and define clean theme tokens.
3. Redesign `Hero.tsx`, `Features.tsx`, `Auth.tsx`, and `Workbench.tsx`.
4. Install necessary Shadcn components.
