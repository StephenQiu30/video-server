## Why

The current Umi/AntD frontend is functional but lacks the premium aesthetic and modern UI patterns expected for a competitive SaaS product. Switching to Vite + React + Tailwind CSS + Shadcn UI + Radix UI allows for maximum flexibility, visually stunning designs, and better alignment with modern frontend standards. This redesign aims to "WOW" users with a premium first impression and a more intuitive workbench experience.

## What Changes

- **New Tech Stack**: Replace the existing Umi/AntD Pro setup with a modern Vite + React + Tailwind CSS + Shadcn UI foundation.
- **Premium Landing Page**: A completely redesigned landing page with a high-impact hero section, smooth micro-animations, and clear value proposition displays.
- **Redesigned Workbench**: A state-of-the-art download workspace where users can submit URLs and select specific resolutions (e.g., 4K, 1080p).
- **AI Feature Hooks**: Pre-designed UI components for upcoming AI features like video summaries, mind maps, and comment analysis.
- **Design System**: Implementation of a consistent, premium design system using Tailwind tokens and Shadcn components.

## Capabilities

### New Capabilities
- `frontend-landing-page`: High-conversion responsive landing page with modern aesthetics.
- `frontend-workbench-ui`: Advanced workspace for video task management and resolution selection.

### Modified Capabilities
- `web-download-workspace`: The existing frontend capability will be fully replaced and expanded with the new UI.

## Impact

- `apps/web`: Complete replacement of the existing Umi-based frontend.
- `apps/api`: The API might need minor updates to support more granular resolution selection if not already fully exposed.
- `infra/docker`: Dockerfile for the web component will need updates for the new build process.
