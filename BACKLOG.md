# Gap-based Backlog (Step-2)

## A. Flask architecture retained
- [x] Keep Flask as primary web backend.
- [x] FastAPI adapter evaluated as optional; Flask retained for single-user scope to minimize complexity.

## B. Web module parity
- [x] Added web routes/pages for Staff, POS, Settings, Receipt.
- [x] Kitchen/KDS web module added with queue + status update actions.
- [x] Expanded CRUD depth for web parity: menu category/item create/toggle/delete and kitchen flow actions.

## C. RBAC hardening
- [x] Centralized permission map and web permission decorators.
- [x] Enforce permission checks on mutable API endpoints for tables/orders/inventory/reservations/staff/pos/settings.

## D. Migration strategy
- [x] Added Alembic env and baseline version migration.
- [x] Add incremental revision for schema-alignment fields (0002).

## E. Deploy stack
- [x] Added Dockerfile, docker-compose, .env.example.
- [x] Added production profile (gunicorn, reverse proxy, TLS) via docker-compose.prod + nginx config.

## F. Quality gates
- [x] Added pytest-based smoke tests.
- [x] Expanded test coverage with service/integration web authz + menu CRUD tests.
