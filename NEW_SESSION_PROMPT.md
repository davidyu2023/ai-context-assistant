# Quick Start Prompt for New Claude Code Session

**Copy and paste this at the start of your new session at https://github.com/davidyu2023/lets-go**

---

Hi! I'm starting a new tour guide application. I've already completed architectural planning in a previous session.

**Full Architecture Document**: See `TOUR_GUIDE_APP_ARCHITECTURE.md` (read this first for complete context)

## Quick Summary

**Project**: Multi-tenant tour guide app (like Meetup.com but for location-based tours)
**Solo Developer**: Bootstrapping, no funding, flexible timeline
**Target**: MVP in 12-16 weeks, handle 10K-50K concurrent users

## Key Decisions Already Made

**Architecture**:
- ✅ Modular Monolith (NestJS backend)
- ✅ CQRS for program management
- ✅ Row-Level Security (PostgreSQL) for multi-tenancy
- ✅ Offline-first mobile (React Native with SQLite)
- ✅ Versioned immutability for tours

**Tech Stack**:
- Monorepo: Turborepo + pnpm
- Backend: NestJS + Prisma + PostgreSQL + Redis
- Web Admin: React + TypeScript + Vite + shadcn/ui
- Mobile: React Native (Expo) + SQLite
- Payments: Stripe
- Media: Cloudflare R2 + CDN

**Infrastructure** (MVP): $0-20/month using free tiers

## What I Need You To Do

**Start with Task 1**: Set up the monorepo structure

Create:
```
lets-go/
├── package.json (root)
├── pnpm-workspace.yaml
├── turbo.json
├── packages/
│   ├── backend/          # NestJS
│   ├── web-admin/        # React admin panel
│   ├── mobile/           # React Native (Expo)
│   └── shared/           # TypeScript types, Zod schemas
├── .github/
│   └── workflows/        # CI/CD
└── README.md
```

**Specific requirements**:
1. Use TypeScript throughout (strict mode)
2. Configure path aliases for cross-package imports (`@shared/types`)
3. Add ESLint + Prettier configs
4. Include `.gitignore` (node_modules, .env, etc.)
5. Set up basic CI (lint + type-check on PR)

After completing Task 1, I'll ask you to scaffold each package individually.

**Please read `TOUR_GUIDE_APP_ARCHITECTURE.md` first for full context, then let's start with the monorepo setup.**
