# Gap-based Backlog (Step-2)

## A. Flask architecture retained
- [x] Keep Flask as primary web backend.
- [ ] Evaluate optional FastAPI adapter only if needed later.

## B. Web module parity
- [x] Added web routes/pages for Staff, POS, Settings, Receipt.
- [x] Kitchen/KDS web module added with queue + status update actions.
- [ ] Expand all CRUD/actions to match desktop feature depth.

## C. RBAC hardening
- [x] Centralized permission map and web permission decorators.
- [x] Enforce permission checks on mutable API endpoints for tables/orders/inventory/reservations/staff/pos/settings.

## D. Migration strategy
- [x] Added Alembic env and baseline version migration.
- [x] Add incremental revision for schema-alignment fields (0002).
- [ ] Enforce permission checks on every mutable API endpoint.

## D. Migration strategy
- [x] Added Alembic env and baseline version migration.
- [ ] Add incremental revisions for future schema changes.

## E. Deploy stack
- [x] Added Dockerfile, docker-compose, .env.example.
- [ ] Add production profile (gunicorn, reverse proxy, TLS).

## F. Quality gates
- [x] Added pytest-based smoke tests.
- [ ] Expand to service-level + integration + E2E tests.
