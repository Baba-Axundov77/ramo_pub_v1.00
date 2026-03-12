# AGENTS.md

## Must-follow constraints
- `OPTIMIZATIONS.md` is audit-only; do not implement runtime changes from it unless explicitly requested.
- Do not mutate schema in runtime code (`database/connection.py`); use Alembic migrations for schema changes.
- Inventory deductions must lock rows with `SELECT FOR UPDATE`.
- Keep checkout/payment flow in a single DB transaction.
- WebSocket event names must stay backward-compatible (`kds_orders_update`, `order_ready`, etc.).
- Preserve luxury UI palette: gold `#c6a659` on dark `#020617`.

## Validation before finishing
- Run `pytest -q`.
- Run `python -m compileall modules web database`.
- For WebSocket handler edits, verify client cleanup prevents `kds_clients` growth.

## Repo-specific conventions
- Put business logic in `modules/*/*_service.py`; keep `web/routes/*.py` thin.
- In routes, use request-scoped `g.db`; do not create ad-hoc global DB sessions.
- Prefer soft-delete flags (`is_active`, `is_cancelled`) unless hard delete is explicitly required.
- Eliminate N+1 query patterns with batch loading/subqueries.
- Analytics endpoints must use cache stampede protection.

## Important locations
- DB connection/session management: `database/connection.py`
- ORM models: `database/models.py`
- Checkout + inventory flow: `modules/pos/pos_service.py`
- WebSocket handlers: `web/routes/websocket_*.py`
- Analytics hot paths: `modules/reports/report_service.py`

## Change safety rules
- Do not change existing API response keys in `web/routes` without explicit request.
- Preserve numeric accuracy in reports.
- Keep WebSocket payload structure backward-compatible.
- Maintain backward-compatible database deployments.

## Known gotchas
- `kds_clients` can leak without cleanup/TTL handling.
- Analytics caching is prone to stampede without Redis `SETNX` locking.
- New endpoints often miss `permission_required` checks.
- Soft-delete fields differ by table; confirm model fields before delete logic.
