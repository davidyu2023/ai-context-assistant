# Tour Guide Application - Architecture & Implementation Plan

## Project Overview

**Repository**: https://github.com/davidyu2023/lets-go

**Vision**: A multi-tenant tour guide application that enables tour creators to design rich, location-based experiences and allows tourists to participate in guided tours with offline-first mobile capabilities.

**Context**: Solo developer, no funding, flexible timeline. Goal is to build an MVP that can be monetized and scaled as traction grows.

---

## Key Business Requirements

### User Personas

1. **Tour Creator/Host**
   - Creates tour programs (locations, media, ordering)
   - Uses web-based dashboard (desktop/tablet)
   - Complex structural writes, low frequency
   - Requires stable connectivity

2. **Tour Guide**
   - May or may not be a creator
   - Can select/purchase tour programs
   - Starts sessions (sets meeting time/location)
   - Leads groups through tours

3. **Tourist**
   - Views available programs and active sessions
   - Joins sessions
   - Mobile-first experience
   - Requires offline capabilities

### Core Features

- **Program Management**: Create immutable tour programs with locations, media (images/audio/video), and sequencing
- **Session Management**: Track progress of tourists and guides through tours (duration: hours to years)
- **Multi-Tenancy**: Row-level isolation for different tour operators
- **Social Features**: Comments and discussions per session
- **Monetization**: Stripe integration for host subscriptions and tourist payments
- **Offline-First Mobile**: Work without connectivity, sync when available

---

## Critical Load Profile Analysis

### Actual Load (NOT Online Gaming)

```
100K concurrent users distribution:
- 70% browsing programs (mostly cached reads)
- 20% in active tours (location updates)
- 10% idle/background

Real load calculations:
- Browsing: 70K users × 0.1 / 30 = ~233 queries/sec (90% cache hits)
- Active tours: 20K users / 180 = ~111 location updates/sec
- Total: ~350 queries/sec, ~111 writes/sec

Key insight: Real-life interactions = much lower frequency than online games
```

### Capacity by Phase

| Phase | Architecture | Concurrent Users | Monthly Cost |
|-------|--------------|------------------|--------------|
| Phase 1 (MVP) | Single server + PG + Redis | 10K-50K | $0-200 |
| Phase 2 (Scale) | Multi-server + replicas | 50K-150K | $300-800 |
| Phase 3 (Optimize) | Multi-region + sharding | 150K-500K+ | $1K-3K |

---

## Architecture Decisions

### 1. Modular Monolith (Not Microservices)

**Decision**: Start with a modular monolith, extract to microservices only when needed

**Rationale**:
- Simpler operations for solo developer
- Strict module boundaries allow future extraction
- Avoid distributed transaction complexity
- Single deployment unit reduces DevOps overhead

**Pattern**:
```
tour-guide-app/
├── packages/
│   ├── backend/           # NestJS - Modular Monolith
│   │   ├── programs/      # Bounded context
│   │   ├── sessions/      # Bounded context
│   │   ├── users/         # Bounded context
│   │   └── payments/      # Bounded context
│   ├── web-admin/         # React admin panel
│   ├── mobile/            # React Native
│   └── shared/            # Types, validation, utils
```

---

### 2. CQRS (Command Query Responsibility Segregation)

**Decision**: Implement CQRS for program management from day one

**Rationale**:
- **Write side (Command)**: Complex validation, business rules (Host creates tours)
- **Read side (Query)**: Denormalized, optimized for mobile consumption (Tourists browse)
- Different scaling characteristics (high reads, low writes)
- Enables aggressive caching without cache invalidation complexity

**Implementation**:
```typescript
// Command Side (Write Model) - Normalized
class CreateProgramCommand {
  creatorId: string;
  title: string;
  locations: LocationDTO[];
}

@CommandHandler(CreateProgramCommand)
class CreateProgramHandler {
  async execute(cmd: CreateProgramCommand) {
    // Complex validation, business rules
    const program = await this.repo.create(cmd);
    await this.eventBus.publish(new ProgramCreatedEvent(program));
  }
}

// Query Side (Read Model) - Denormalized
@QueryHandler(GetProgramQuery)
class GetProgramHandler {
  async execute(query: GetProgramQuery) {
    // Optimized read from denormalized view
    return this.readModel.findById(query.id);
  }
}
```

---

### 3. Multi-Tenancy: Row-Level Security (RLS)

**Decision**: Use PostgreSQL Row-Level Security for tenant isolation

**Rationale**:
- "Pool" model (shared schema) is cost-effective for many small tenants
- RLS provides defense-in-depth security below application layer
- Automatic enforcement even if application code has bugs
- Simpler than managing separate schemas/databases per tenant

**Implementation**:
```sql
-- Every table has tenant_id
CREATE TABLE tours (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL,
  ...
);

-- Enable RLS
ALTER TABLE tours ENABLE ROW LEVEL SECURITY;

-- Policy automatically filters by tenant
CREATE POLICY tenant_isolation ON tours
  USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

```typescript
// Middleware sets tenant context per request
@Injectable()
class TenantMiddleware {
  async use(req: Request, res: Response, next: Function) {
    const tenantId = req.user.tenantId;
    await prisma.$executeRaw`SET app.current_tenant = ${tenantId}`;
    next();
  }
}
```

---

### 4. Immutability via Versioning

**Decision**: Tour programs become immutable once a session starts

**Rationale**:
- Prevents breaking user experience mid-tour
- Enables temporal queries ("What did this tour look like in 2023?")
- Audit trail for disputes

**Pattern**: Copy-on-Write
```typescript
async editTour(tourId: string, edits: Partial<Tour>) {
  const tour = await this.findById(tourId);
  const hasActiveSessions = await this.sessionService.hasActive(tourId);

  if (hasActiveSessions) {
    // Clone to new version
    const newVersion = await this.cloneTourVersion(tour);
    await this.applyEdits(newVersion.id, edits);
    return newVersion;
  } else {
    // Safe to edit in place
    await this.applyEdits(tourId, edits);
  }
}
```

**Schema**:
```sql
CREATE TABLE tour_versions (
  id UUID PRIMARY KEY,
  tour_id UUID NOT NULL,
  version_number INT NOT NULL,
  is_published BOOLEAN DEFAULT false,
  snapshot_data JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sessions (
  id UUID PRIMARY KEY,
  tour_version_id UUID NOT NULL REFERENCES tour_versions(id),
  -- Session always references specific version
);
```

---

### 5. Offline-First Mobile Architecture

**Decision**: Mobile device is source of truth, server is sync hub

**Rationale**:
- Tours happen in areas with poor connectivity (hiking, remote sites, international)
- User experience cannot depend on network availability
- Local database enables instant UI updates

**Pattern**: Local DB + Outbox Sync
```typescript
// Local SQLite is the source of truth
class TourRepository {
  async getTour(id: string): Promise<Tour> {
    // ALWAYS read from local DB, never API
    return await localDb.tours.findById(id);
  }

  async updateProgress(sessionId: string, waypoint: Waypoint) {
    // Write locally FIRST
    await localDb.progress.insert({ sessionId, waypoint, syncStatus: 'PENDING' });

    // Queue for background sync
    await syncQueue.enqueue({
      action: 'UPDATE_PROGRESS',
      data: { sessionId, waypoint }
    });
  }
}

// Background sync worker
class SyncWorker {
  async run() {
    const pending = await localDb.syncQueue.where({ status: 'PENDING' }).findMany();

    for (const item of pending) {
      try {
        await api.sync(item.data);
        await localDb.syncQueue.update(item.id, { status: 'SYNCED' });
      } catch (error) {
        // Retry with exponential backoff
        await this.scheduleRetry(item);
      }
    }
  }
}
```

---

### 6. Session State Management

**Decision**: Use simple state machine + event log (NOT full Event Sourcing for MVP)

**Rationale**:
- Full Event Sourcing adds 4-6 weeks of complexity
- Event log provides audit trail without full replay overhead
- Hybrid approach: Current state in table, events for history

**Pattern**:
```typescript
// Current state (CRUD)
CREATE TABLE sessions (
  id UUID PRIMARY KEY,
  tour_version_id UUID NOT NULL,
  guide_id UUID NOT NULL,
  status VARCHAR(20) NOT NULL, -- DRAFT, ACTIVE, PAUSED, COMPLETED
  current_waypoint_index INT,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  state_data JSONB
);

// Event log (append-only)
CREATE TABLE session_events (
  id UUID PRIMARY KEY,
  session_id UUID NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  user_id UUID,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  payload JSONB NOT NULL
);

// Combined approach
class SessionService {
  async updateProgress(sessionId: string, waypointId: string, userId: string) {
    // 1. Append event (audit trail)
    await this.eventLog.append({
      sessionId,
      eventType: 'WAYPOINT_ARRIVED',
      userId,
      payload: { waypointId }
    });

    // 2. Update current state (for fast queries)
    await this.sessions.update(sessionId, {
      currentWaypointIndex: newIndex,
      stateData: { lastUpdate: new Date() }
    });

    // 3. Invalidate cache
    await redis.del(`session:${sessionId}`);
  }
}
```

**When to add Temporal.io**: Phase 2, if multi-month sessions become common

---

### 7. Defer Complex Patterns to Phase 2/3

**Deferred to Phase 2**:
- ❌ Temporal.io (use simple state machine + BullMQ)
- ❌ Full Event Sourcing (use event log + current state)
- ❌ Kalman Filter for GPS (use OS fused location)
- ❌ Predictive prefetching (download next 2 waypoints sequentially)
- ❌ Elasticsearch (use PostgreSQL full-text search)
- ❌ WebSocket live chat (async comments sufficient)

**Deferred to Phase 3**:
- ❌ Multi-region deployment
- ❌ Database sharding
- ❌ Advanced analytics (Clickhouse/BigQuery)
- ❌ Chaos engineering

---

## Technology Stack

### Monorepo
- **Tool**: Turborepo
- **Package Manager**: pnpm
- **Why**: Fastest build tool, great caching, simple config

### Backend
- **Framework**: NestJS (TypeScript)
  - Modular architecture matches domain boundaries
  - Excellent DI container
  - Built-in CQRS support (`@nestjs/cqrs`)
  - Decorator-based (AI-friendly)
- **Database**: PostgreSQL 15+
  - JSONB for flexible metadata
  - Row-Level Security for multi-tenancy
  - PostGIS for geospatial queries
- **ORM**: Prisma
  - Type-safe queries
  - Excellent migrations
  - Auto-generated types
- **Cache**: Redis
  - Session state for active tours
  - Read-through cache for programs
  - BullMQ for job queues
- **Auth**: Passport.js + JWT
- **Queue**: BullMQ (Redis-based)

### Web Admin
- **Framework**: React 18 + TypeScript
- **Build**: Vite
- **UI Components**: shadcn/ui (Tailwind CSS)
- **Maps**: Mapbox GL JS
- **State**: Zustand (simpler than Redux)
- **Forms**: React Hook Form + Zod
- **Deployment**: Vercel (free tier)

### Mobile
- **Framework**: React Native (Expo)
  - Faster development than native
  - OTA updates
  - Shared code with web (types, validation)
- **Local DB**: expo-sqlite
- **Maps**: react-native-mapbox-gl
- **Location**: expo-location
- **Notifications**: expo-notifications
- **Media**: expo-av
- **Deployment**: EAS Build

### Shared
- **Types**: TypeScript interfaces (shared package)
- **Validation**: Zod schemas (backend + frontend)
- **API Contracts**: OpenAPI/Swagger

### Infrastructure (MVP - Free Tier Focus)
- **Database**: Supabase (500MB free) or Railway ($20-25)
- **Redis**: Upstash (10K commands/day free)
- **Backend Hosting**: Railway or Fly.io
- **Web Hosting**: Vercel (free)
- **Media Storage**: Cloudflare R2 (10GB free)
- **CDN**: Cloudflare (unlimited bandwidth FREE)
- **Email**: Resend (3K emails/month free)
- **Payments**: Stripe

### Cost Breakdown

| Users | Infrastructure/Month | Expected Revenue/Month | Profit |
|-------|---------------------|----------------------|--------|
| 0-500 | $0-20 (free tiers) | $0-500 | -$20 to +$480 |
| 500-5K | $60-115 | $500-3K | +$385 to +$2.9K |
| 5K-50K | $200-400 | $3K-20K | +$2.6K to +$19.8K |
| 50K-100K | $800-1.5K | $20K-100K | +$18.5K to +$98.5K |

**Key**: Infrastructure is mostly fixed cost ($50-95/month base), variable costs are revenue-tied (Stripe fees).

---

## Database Schema (Core Tables)

### Multi-Tenancy
```sql
CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(100) UNIQUE NOT NULL,
  subscription_tier VARCHAR(50) NOT NULL, -- FREE, PRO, ENTERPRISE
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Users & Auth
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  roles VARCHAR(50)[] NOT NULL, -- {TOURIST, GUIDE, CREATOR, ADMIN}
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
```

### Tour Programs (Versioned)
```sql
CREATE TABLE tours (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  creator_id UUID NOT NULL REFERENCES users(id),
  title VARCHAR(255) NOT NULL,
  description TEXT,
  is_published BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE tour_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tour_id UUID NOT NULL REFERENCES tours(id),
  version_number INT NOT NULL,
  is_locked BOOLEAN DEFAULT false, -- True if any session uses this version
  snapshot_data JSONB NOT NULL, -- Full denormalized tour data
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(tour_id, version_number)
);

CREATE TABLE waypoints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tour_version_id UUID NOT NULL REFERENCES tour_versions(id) ON DELETE CASCADE,
  order_index INT NOT NULL,
  name VARCHAR(255) NOT NULL,
  latitude DECIMAL(10, 8) NOT NULL,
  longitude DECIMAL(11, 8) NOT NULL,
  radius_meters INT DEFAULT 50, -- Geofence radius
  media_urls JSONB, -- {images: [], audio: [], video: []}
  description TEXT,
  UNIQUE(tour_version_id, order_index)
);

-- Enable RLS
ALTER TABLE tours ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON tours
  USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

### Sessions
```sql
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  tour_version_id UUID NOT NULL REFERENCES tour_versions(id),
  guide_id UUID NOT NULL REFERENCES users(id),
  status VARCHAR(20) NOT NULL, -- DRAFT, ACTIVE, PAUSED, COMPLETED
  current_waypoint_index INT DEFAULT 0,
  max_participants INT,
  meeting_location JSONB, -- {lat, lng, address}
  scheduled_start_time TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  state_data JSONB, -- Flexible state storage
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE session_participants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id),
  current_waypoint_index INT DEFAULT 0,
  joined_at TIMESTAMPTZ DEFAULT NOW(),
  last_active_at TIMESTAMPTZ DEFAULT NOW(),
  progress_data JSONB, -- {visitedWaypoints: [], completedAt: {}}
  UNIQUE(session_id, user_id)
);

-- Event log for audit trail
CREATE TABLE session_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id),
  user_id UUID REFERENCES users(id),
  event_type VARCHAR(50) NOT NULL, -- STARTED, WAYPOINT_ARRIVED, WAYPOINT_DEPARTED, COMPLETED
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  payload JSONB NOT NULL
);

CREATE INDEX idx_session_events_session ON session_events(session_id, timestamp);

ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON sessions
  USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

### Social Features
```sql
CREATE TABLE comments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id),
  parent_id UUID REFERENCES comments(id), -- For nested comments
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_comments_session ON comments(session_id, created_at);

CREATE TABLE ratings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tour_id UUID NOT NULL REFERENCES tours(id),
  user_id UUID NOT NULL REFERENCES users(id),
  session_id UUID REFERENCES sessions(id),
  rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  review TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(tour_id, user_id)
);
```

### Payments
```sql
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  stripe_subscription_id VARCHAR(255) UNIQUE,
  status VARCHAR(50) NOT NULL, -- ACTIVE, CANCELED, PAST_DUE
  current_period_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  session_id UUID REFERENCES sessions(id),
  stripe_payment_intent_id VARCHAR(255) UNIQUE,
  amount_cents INT NOT NULL,
  status VARCHAR(50) NOT NULL, -- PENDING, SUCCEEDED, FAILED
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Implementation Phases

### Phase 1: Monetizable MVP (12-16 weeks)

**Goal**: Launch with 100-500 users, generate first revenue

#### Week 1-2: Foundation
- ✅ Turborepo monorepo setup (backend, web-admin, mobile, shared)
- ✅ NestJS backend skeleton (auth module, tenant module)
- ✅ Prisma + PostgreSQL (schema, migrations, RLS middleware)
- ✅ React web admin shell (routing, layout, auth)
- ✅ React Native mobile shell (Expo, navigation, auth)

#### Week 3-5: Program Management (CQRS)
- ✅ Backend: Program CQRS module
  - Commands: CreateProgram, UpdateProgram, PublishProgram
  - Queries: GetProgram, SearchPrograms (PostgreSQL full-text search)
  - Versioning logic (copy-on-write)
- ✅ Web Admin: Tour Editor
  - Mapbox integration (interactive map)
  - Waypoint CRUD (drag to reorder)
  - Media upload (Cloudflare R2 pre-signed URLs)
- ✅ Mobile: Tour Browsing
  - List tours (geospatial search: "near me")
  - Tour detail screen (map preview, waypoints)

#### Week 6-8: Session Management
- ✅ Backend: Session module
  - Create/join/leave session
  - Progress tracking (simple state machine)
  - Cache active sessions in Redis
- ✅ Mobile: Offline-First Tour Participation
  - SQLite local DB (sync tour data)
  - Geofencing (expo-location, no Kalman filter)
  - Media playback (pre-downloaded via sync)
  - Outbox pattern (queue local changes for sync)

#### Week 9-10: Monetization
- ✅ Stripe integration
  - Host subscriptions (Free: 1 program, Pro: unlimited)
  - Tourist payment for premium tours
  - Webhook handling (BullMQ async processing)
- ✅ Basic analytics dashboard (host revenue, participant count)

#### Week 11-12: Social Features
- ✅ Comments on sessions (PostgreSQL + Redis cache)
- ✅ Ratings/reviews for tours
- ✅ User profiles

#### Week 13-16: Polish & Launch
- ✅ Mobile app polish (onboarding flow, push notifications)
- ✅ Email notifications (tour reminders via Resend)
- ✅ Testing (Jest unit tests, E2E with Detox)
- ✅ Deployment automation (GitHub Actions CI/CD)
- ✅ App Store / Play Store submission

**Capacity**: 10K-50K concurrent users
**Infrastructure**: $0-200/month

---

### Phase 2: Scale (8-12 weeks)

**Trigger**: Revenue > $1K/month, 5K+ users

- ✅ PostgreSQL read replicas (route GET to replicas)
- ✅ Horizontal API server scaling (load balancer)
- ✅ WebSocket gateway for live chat (Redis pub/sub)
- ✅ Advanced search (Elasticsearch or Typesense)
- ✅ Analytics (Clickhouse or BigQuery for events)
- ✅ Adaptive media prefetching (download based on route)
- ✅ Media transcoding pipeline (Cloudflare Stream or AWS MediaConvert)

**Capacity**: 50K-150K concurrent users
**Infrastructure**: $300-800/month

---

### Phase 3: Optimize (12+ weeks)

**Trigger**: Revenue > $10K/month, 50K+ users

- ✅ Consider Temporal.io for long-running sessions (if common)
- ✅ Database partitioning (sessions by date range)
- ✅ Multi-region deployment (if global users)
- ✅ Advanced GPS filtering (if accuracy issues)
- ✅ Chaos engineering & load testing (k6 with GPX data)

**Capacity**: 150K-500K+ concurrent users
**Infrastructure**: $1K-3K/month

---

## Key Patterns & Best Practices

### CQRS Implementation
```typescript
// 1. Define commands and queries
export class CreateTourCommand {
  constructor(
    public readonly creatorId: string,
    public readonly title: string,
    public readonly waypoints: WaypointDTO[]
  ) {}
}

export class GetTourQuery {
  constructor(public readonly id: string) {}
}

// 2. Command handler (write model)
@CommandHandler(CreateTourCommand)
export class CreateTourHandler implements ICommandHandler<CreateTourCommand> {
  constructor(
    private readonly repo: TourRepository,
    private readonly eventBus: EventBus
  ) {}

  async execute(command: CreateTourCommand): Promise<string> {
    // Validation
    if (command.waypoints.length < 2) {
      throw new BadRequestException('Tour must have at least 2 waypoints');
    }

    // Create normalized entities
    const tour = await this.repo.create({
      creatorId: command.creatorId,
      title: command.title,
    });

    const version = await this.repo.createVersion(tour.id, 1);

    await this.repo.createWaypoints(version.id, command.waypoints);

    // Publish domain event
    this.eventBus.publish(new TourCreatedEvent(tour.id));

    return tour.id;
  }
}

// 3. Query handler (read model)
@QueryHandler(GetTourQuery)
export class GetTourHandler implements IQueryHandler<GetTourQuery> {
  constructor(private readonly readModel: TourReadModel) {}

  async execute(query: GetTourQuery): Promise<TourDTO> {
    // Check cache first
    const cached = await redis.get(`tour:${query.id}`);
    if (cached) return JSON.parse(cached);

    // Fetch denormalized view
    const tour = await this.readModel.findById(query.id);

    // Cache for 1 hour
    await redis.setex(`tour:${query.id}`, 3600, JSON.stringify(tour));

    return tour;
  }
}

// 4. Event listener (update read model)
@EventsHandler(TourCreatedEvent)
export class TourCreatedEventHandler implements IEventHandler<TourCreatedEvent> {
  async handle(event: TourCreatedEvent) {
    // Build denormalized read model
    const tour = await this.buildTourReadModel(event.tourId);
    await this.readModel.save(tour);
  }
}
```

### Row-Level Security Pattern
```typescript
// Middleware to set tenant context
@Injectable()
export class TenantMiddleware implements NestMiddleware {
  async use(req: Request, res: Response, next: NextFunction) {
    const user = req.user as JwtPayload;

    if (!user?.tenantId) {
      throw new UnauthorizedException('Tenant context required');
    }

    // Set PostgreSQL session variable
    await this.prisma.$executeRawUnsafe(
      `SET app.current_tenant = '${user.tenantId}'`
    );

    next();
  }
}

// In main.ts
app.use(new TenantMiddleware().use);
```

### Offline-First Mobile Sync
```typescript
// Mobile: Sync Manager
export class SyncManager {
  private syncQueue: SyncQueue;
  private isOnline: boolean;

  async queueAction(action: SyncAction) {
    // Save to local outbox
    await this.syncQueue.enqueue({
      id: uuid(),
      action: action.type,
      payload: action.data,
      status: 'PENDING',
      createdAt: new Date(),
      retryCount: 0
    });

    // Trigger sync if online
    if (this.isOnline) {
      this.processQueue();
    }
  }

  async processQueue() {
    const pending = await this.syncQueue.getPending();

    for (const item of pending) {
      try {
        // Send to server
        await api.sync(item.action, item.payload);

        // Mark as synced
        await this.syncQueue.updateStatus(item.id, 'SYNCED');
      } catch (error) {
        // Exponential backoff
        const delay = Math.pow(2, item.retryCount) * 1000;
        await this.syncQueue.scheduleRetry(item.id, delay);
      }
    }
  }

  // Delta sync: pull server changes
  async pullChanges() {
    const lastSync = await this.getLastSyncTimestamp();

    const delta = await api.getDelta(lastSync);

    // Apply to local DB
    for (const change of delta.changes) {
      await this.applyChange(change);
    }

    await this.setLastSyncTimestamp(delta.serverTimestamp);
  }
}
```

### Geofencing with Rolling Window (iOS 20 region limit)
```typescript
// Mobile: Geofence Manager
export class GeofenceManager {
  private readonly MAX_GEOFENCES = 20; // iOS limit
  private currentLocation: Location;

  async updateGeofences(sessionId: string) {
    const session = await localDb.sessions.findById(sessionId);
    const waypoints = session.waypoints;

    // Calculate distances to all unvisited waypoints
    const distances = waypoints
      .filter(wp => !wp.visited)
      .map(wp => ({
        waypoint: wp,
        distance: this.calculateDistance(this.currentLocation, wp.location)
      }))
      .sort((a, b) => a.distance - b.distance);

    // Register nearest N waypoints
    const nearest = distances.slice(0, this.MAX_GEOFENCES);

    // Clear existing geofences
    await Location.removeAllGeofences();

    // Register new set
    for (const { waypoint } of nearest) {
      await Location.startGeofencingAsync(waypoint.id, {
        latitude: waypoint.location.latitude,
        longitude: waypoint.location.longitude,
        radius: waypoint.radiusMeters || 50
      });
    }
  }

  // Called when user enters geofence
  async onGeofenceEnter(waypointId: string) {
    // Update local state
    await localDb.progress.markVisited(waypointId);

    // Trigger media playback
    await this.mediaPlayer.play(waypointId);

    // Queue sync to server
    await this.syncManager.queueAction({
      type: 'WAYPOINT_ARRIVED',
      data: { waypointId, timestamp: new Date() }
    });

    // Re-calculate geofences (rolling window)
    await this.updateGeofences(this.currentSessionId);
  }
}
```

---

## Immediate Next Steps (New Session)

When you start the new session at `https://github.com/davidyu2023/lets-go`, begin with:

### Task 1: Repository Setup
```
Initialize monorepo structure:
- Set up Turborepo with pnpm workspaces
- Create packages: backend, web-admin, mobile, shared
- Configure TypeScript paths for cross-package imports
- Add ESLint, Prettier configs
```

### Task 2: Backend Foundation
```
Set up NestJS backend:
- Install dependencies: @nestjs/core, @nestjs/common, prisma, etc.
- Create module structure: auth, users, tenants, programs, sessions
- Configure Prisma with PostgreSQL
- Implement JWT authentication with Passport
- Create tenant middleware for RLS
```

### Task 3: Database Schema
```
Create Prisma schema:
- Define all core tables (tenants, users, tours, tour_versions, waypoints, sessions, etc.)
- Add RLS policies in migration SQL
- Generate Prisma Client
- Seed initial data (test tenant, users)
```

### Task 4: Web Admin Shell
```
Set up React admin panel:
- Vite + React + TypeScript
- Install shadcn/ui components
- Create auth flow (login, register)
- Dashboard layout (sidebar, routing)
- Integrate with backend API
```

### Task 5: Mobile Shell
```
Set up React Native app:
- expo init with TypeScript
- Navigation setup (react-navigation)
- Auth screens (login, register)
- Configure expo-sqlite for local DB
- Test on iOS/Android simulators
```

---

## References & Resources

### Architecture Patterns
- CQRS: https://docs.microsoft.com/en-us/azure/architecture/patterns/cqrs
- Event Sourcing: https://martinfowler.com/eaaDev/EventSourcing.html
- Offline-First: https://offlinefirst.org/

### Technology Documentation
- NestJS: https://docs.nestjs.com/
- Prisma: https://www.prisma.io/docs
- React Native: https://reactnative.dev/docs/getting-started
- Expo: https://docs.expo.dev/
- Turborepo: https://turbo.build/repo/docs

### Geospatial
- Mapbox GL JS: https://docs.mapbox.com/mapbox-gl-js/
- React Native Mapbox: https://github.com/rnmapbox/maps
- Expo Location: https://docs.expo.dev/versions/latest/sdk/location/

### Payments
- Stripe Docs: https://stripe.com/docs

---

## Success Metrics

### MVP Launch (Week 16)
- ✅ 10+ tour creators signed up
- ✅ 50+ tourists tried a tour
- ✅ $100+ in revenue (validates monetization)
- ✅ Mobile app published to App Store + Play Store
- ✅ 95%+ uptime

### Product-Market Fit (Month 6)
- ✅ 100+ active creators
- ✅ 1,000+ tourists
- ✅ $1,000+ MRR (monthly recurring revenue)
- ✅ 70%+ tour completion rate
- ✅ 4.5+ star rating on app stores

### Scale Milestone (Month 12)
- ✅ 500+ active creators
- ✅ 10,000+ tourists
- ✅ $10,000+ MRR
- ✅ International expansion (multi-language)

---

## Contact & Session Context

**Developer**: Solo developer, bootstrapping
**Timeline**: Flexible (12-16 weeks for MVP)
**Budget**: Minimal infrastructure cost, leverage free tiers
**Working Style**: Phased approach with Claude Code assistance

**Repository**: https://github.com/davidyu2023/lets-go

---

*This document serves as the architectural foundation for the lets-go tour guide application. All major technical decisions have been made. Implementation can begin immediately following the phased plan outlined above.*
