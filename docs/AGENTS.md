# AGENTS.md

## Must-follow constraints
- `OPTIMIZATIONS.md` is audit-only; never implement runtime changes from that file
- Schema changes must use Alembic migrations; never mutate schema at runtime in `database/connection.py`
- Inventory/stock updates MUST use `SELECT FOR UPDATE` to prevent overselling
- Checkout flow must remain in single DB transaction; never split commits
- WebSocket events must follow established naming: `kds_orders_update`, `order_ready`, etc.
- UI color palette: gold (#c6a659) on dark (#020617) - never deviate
- Never break backward compatibility of database schema during deployment

## Validation before finishing
- Run: `pytest -q`
- Run: `python -m compileall modules web database`
- Verify: WebSocket connections don't leak (check `kds_clients` dict cleanup)

## Repo-specific conventions
- Business logic lives in `modules/*/*_service.py`; keep `web/routes/*.py` thin and delegate
- Use `g.db` (Flask request-scoped session) in routes; never create ad-hoc global sessions
- Use soft-delete pattern (`is_active`, `is_cancelled`) unless hard delete is explicitly required
- All N+1 queries must be eliminated with batch loading or subqueries
- Cache stampede protection required for analytics endpoints

## Important locations
- DB connection management: `database/connection.py`
- Core ORM models: `database/models.py`
- Checkout + inventory flow: `modules/pos/pos_service.py`
- WebSocket handlers: `web/routes/websocket_*.py`
- Analytics hot paths: `modules/reports/report_service.py`

## Change safety rules
- Never modify API response keys in existing `web/routes` unless explicitly requested
- Preserve numerical accuracy in reports refactoring (sums/counts must match exactly)
- WebSocket message structure must remain backward compatible
- All stock-related operations must be atomic and lock rows appropriately

## Known gotchas
- `kds_clients` dict grows without cleanup - must implement TTL in WebSocket handlers
- Analytics cache can cause stampede - always use Redis SETNX lock pattern
- Permission decorators (`permission_required`) are easy to miss when adding new endpoints
- Soft-delete fields vary by table - check model before implementing delete logic
