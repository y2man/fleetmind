# Design system (Phase 2)
- Tokens: CSS variables in `frontend/src/styles/index.css` (dark default, `.dark` class toggles). Tailwind colors map to them: bg, surface, line, ink, muted, electric, violet, ok, warn, danger.
- Components: `components/ui` (Button, GlassCard, Badge, Skeleton, Input, Modal, Dropdown), `components/layout` (AppShell, Sidebar, PageTransition, ThemeToggle), `components/animations` (AnimatedNumber, ParticleBackground).
- Motion: Framer Motion; `MotionConfig reducedMotion="user"` plus a CSS reduced-motion rule. Particles are skipped entirely when reduced motion is on.
- GSAP and Three.js arrive with the landing page (Phase 3).
- Showcase route: `/app/design`.

## Phase 3
- Landing: `features/landing` (GSAP hero and scroll reveals, optional lazy-loaded Three.js globe skipped under reduced motion).
- Dashboard: `features/dashboard`. Demo data lives in `demoData.ts` and is loaded through TanStack Query, so Phase 5 only swaps the query function for the real API.
- All statistics, testimonials, pricing and insights are labeled demo content.
