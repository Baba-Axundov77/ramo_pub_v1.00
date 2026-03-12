### 1) Optimization Summary

* Current optimization health is **medium-risk**: the codebase contains strong local optimizations (e.g., `SELECT FOR UPDATE` stock locking in POS service) but suffers from severe **cross-module drift** between API/runtime logic and database trigger logic, plus duplicated source trees that increase maintenance and defect cost.
* Top 3 highest-impact improvements:
  1. **Unify order lifecycle semantics across API + DB triggers** (`ready/paid` in API vs `completed` in trigger) and align trigger joins/columns with current schema.
  2. **Remove duplicated source trees (`src/web` vs `src/web/web`, `src/core/database` vs `src/core/database/database`) via a single canonical package + import redirects.**
  3. **Harden and pool DB access paths in API/WebSocket code** (connection leak-safe patterns, avoid manual cursor usage for hot paths where ORM/session exists).
* Biggest risk if no changes are made: **silent data correctness drift** (analytics, stock, and audit rows diverge from actual order state), compounded by duplicated code that can patch one runtime path while leaving another vulnerable/performance-regressed.

### 2) Findings (Prioritized)

* **Title**: Trigger/API lifecycle mismatch prevents intended trigger optimizations
* **Category**: DB
* **Severity**: Critical
* **Impact**: Analytics consistency, stock correctness, write amplification, operational debugging latency.
* **Evidence**: Trigger runs only on `OLD.status != 'completed' AND NEW.status = 'completed'` in `process_order_completion()`, while API flows set statuses like `'ready'` and model enum lacks `completed` (`OrderStatus` only has `new/preparing/ready/served/paid/cancelled`). Also KDS explicitly updates order to `'ready'`. 
* **Why it’s inefficient**: Trigger-based optimizations/side effects (analytics + stock hooks) are skipped in normal API lifecycle, forcing duplicate logic elsewhere and creating drift.
* **Recommended fix**: Define one canonical lifecycle state machine (DB enum + ORM enum + route handlers). Then rewrite trigger conditions to match real terminal state(s) (`paid` or `served`) and enforce via CHECK/ENUM migration.
* **Tradeoffs / Risks**: Requires migration and careful backward compatibility mapping for existing status rows.
* **Expected impact estimate**: **High** qualitative; eliminates class of silent data drift and duplicate processing.
* **Removal Safety**: Needs Verification
* **Reuse Scope**: service-wide

* **Title**: Trigger SQL references legacy schema names and wrong join key
* **Category**: DB
* **Severity**: Critical
* **Impact**: Trigger failure risk, dead code path, missing analytics/stock updates.
* **Evidence**: Trigger function references `products`, `product_ingredients`, `inventory/current_stock`, while ORM models use `menu_items`, `menu_item_recipes`, `inventory_items/quantity`. It also uses `WHERE t.id = NEW.id` when generating analytics instead of `NEW.table_id`.
* **Why it’s inefficient**: A trigger that targets non-canonical schema objects becomes effectively dead or brittle, causing expensive compensating logic in app code and inconsistent analytics.
* **Recommended fix**: Regenerate trigger function from current ORM schema contract (menu/inventory tables) and correct table join key to `t.id = NEW.table_id`; add migration-time validation tests for function compile + smoke insert/update.
* **Tradeoffs / Risks**: DB migration coordination required; existing reports depending on legacy columns may need mapping.
* **Expected impact estimate**: **High** (correctness + reduced reprocessing and incident cost).
* **Removal Safety**: Needs Verification
* **Reuse Scope**: module + service-wide

* **Title**: Duplicate analytics writes from WebSocket path and trigger design intent
* **Category**: I/O
* **Severity**: High
* **Impact**: Extra DB writes, bloat in `order_analytics`, noisy metrics.
* **Evidence**: `websocket_kds.py` inserts into `order_analytics` in both `order_ready` and `order_analytics` handlers; schema trigger also inserts `order_analytics` on status transition.
* **Why it’s inefficient**: Same business event can be persisted multiple times from separate modules, increasing write load and causing misleading KPIs.
* **Recommended fix**: Centralize analytics write ownership (prefer DB trigger OR one service-layer method). If both are needed, enforce idempotency (`UNIQUE(order_id, event_type)` + `ON CONFLICT DO UPDATE`).
* **Tradeoffs / Risks**: Event model changes may require dashboard query adjustments.
* **Expected impact estimate**: **Medium-High** (write reduction and KPI integrity).
* **Removal Safety**: Likely Safe
* **Reuse Scope**: service-wide

* **Title**: Parallel duplicate code trees increase drift and optimization cost
* **Category**: Cost
* **Severity**: High
* **Impact**: Build time, code review overhead, bug surface area, patch inconsistency risk.
* **Evidence**: Entire mirrored trees exist and are byte-identical now (e.g., `src/web/routes/api_optimized.py` and `src/web/web/routes/api_optimized.py`; `src/core/database/schema_optimized.sql` and `src/core/database/database/schema_optimized.sql`).
* **Why it’s inefficient**: Every optimization/security fix has 2+ patch targets; drift probability rises over time.
* **Recommended fix**: Keep one canonical tree; convert the second to import shims or package aliasing; add CI guard that fails on duplicate drift (checksum or forbidden mirrored paths).
* **Tradeoffs / Risks**: Import paths may break temporarily during consolidation.
* **Expected impact estimate**: **High** maintainability ROI; medium runtime impact indirectly.
* **Removal Safety**: Needs Verification
* **Reuse Scope**: service-wide

* **Title**: DB connection handling lacks guaranteed return-on-error in API hot paths
* **Category**: Reliability
* **Severity**: High
* **Impact**: Pool exhaustion, latency spikes, cascading failure under load.
* **Evidence**: Several endpoints manually `getconn()`/`cursor()` and return connection only on success path (e.g., incremental backup + health check patterns), without `finally`-guarded `putconn`/cursor close.
* **Why it’s inefficient**: Exceptions leak pooled connections, reducing throughput and increasing timeout rate.
* **Recommended fix**: Introduce context manager wrapper for pooled connections/cursors (`with pooled_conn() as conn, conn.cursor() as cur:`) with guaranteed release.
* **Tradeoffs / Risks**: Minor refactor across endpoints.
* **Expected impact estimate**: **Medium-High** under concurrent load.
* **Removal Safety**: Safe
* **Reuse Scope**: module / service-wide

* **Title**: Hardcoded infrastructure credentials and localhost coupling in API config
* **Category**: Reliability
* **Severity**: Medium
* **Impact**: Deployment fragility, secret rotation cost, security breach blast radius.
* **Evidence**: API optimized module hardcodes PostgreSQL host/db/user/password and Redis localhost settings directly in code.
* **Why it’s inefficient**: Prevents environment-specific tuning and forces redeploy for credential changes; increases operational risk.
* **Recommended fix**: Move all connection settings to env/config layer with sane defaults; support pooled param tuning by environment.
* **Tradeoffs / Risks**: Requires config bootstrap update and secret management rollout.
* **Expected impact estimate**: **Medium** cost/reliability gain, high security hardening.
* **Removal Safety**: Safe
* **Reuse Scope**: service-wide

* **Title**: In-memory cache for admin analytics is process-local (multi-worker miss amplification)
* **Category**: Caching
* **Severity**: Medium
* **Impact**: Lower cache hit ratio, repeated expensive queries across workers.
* **Evidence**: `websocket_admin.py` uses a custom `SimpleCache` dictionary and lock in-process; no shared Redis backend for this path.
* **Why it’s inefficient**: In multi-process/gunicorn deployments each worker recomputes KPIs; lock only prevents same-process stampede.
* **Recommended fix**: Migrate admin analytics cache and lock to Redis (`SET NX EX`) using shared keys.
* **Tradeoffs / Risks**: Slight network overhead to Redis.
* **Expected impact estimate**: **Medium** throughput gain for analytics-heavy dashboards.
* **Removal Safety**: Likely Safe
* **Reuse Scope**: module

* **Title**: Reuse/Dead Code opportunity in split service namespaces (`modules` vs `services`)
* **Category**: Build
* **Severity**: Medium
* **Impact**: Maintenance overhead, accidental stale logic usage.
* **Evidence**: Similar functionality appears in both `src/core/modules/*` and `src/core/services/*` trees (e.g., POS and audit modules).
* **Why it’s inefficient**: Duplicate abstractions create uncertainty over active execution path and optimization ownership.
* **Recommended fix**: Mark one namespace canonical, deprecate the other with explicit adapter imports, add static checks to prevent new duplicate implementations.
* **Tradeoffs / Risks**: Requires import-map cleanup.
* **Expected impact estimate**: **Medium** maintainability and defect-rate improvement.
* **Removal Safety**: Needs Verification
* **Reuse Scope**: service-wide

### 3) Quick Wins (Do First)

* Add `finally`-guarded DB pool release/context manager to all `db_pool.getconn()` usage.
* Externalize DB/Redis credentials and tuneable pool options into config/env.
* Add idempotency constraint/index to `order_analytics` inserts (`ON CONFLICT`) to stop duplicate event writes quickly.
* Add CI check that fails when mirrored files diverge in duplicate directory trees.

### 4) Deeper Optimizations (Do Next)

* Consolidate duplicated package trees to a single canonical source layout.
* Redesign order status machine and enforce across DB enum/checks + ORM enum + API/WebSocket handlers.
* Rewrite trigger layer to align with current table/column model and validate via migration tests.
* Move process-local analytics cache to Redis-backed shared cache with stampede lock and bounded TTL policy.

### 5) Validation Plan

* Benchmarks:
  * Load test order-ready/order-paid flows at 50/100/250 concurrent events; compare p95 latency and DB write counts before/after.
  * Run dashboard KPI polling under multi-worker deployment; compare query count and cache hit ratio.
* Profiling strategy:
  * PostgreSQL: `pg_stat_statements`, lock wait analysis, connection utilization.
  * App: request latency histograms, exception counts, pool checkout wait time.
* Metrics to compare before/after:
  * `order_analytics` writes per completed order.
  * DB connection pool exhaustion incidents.
  * p95 API latency for `/api/backup/incremental`, `/api/health`, and dashboard sockets.
  * Cache hit rate for admin analytics.
* Correctness tests:
  * Integration tests verifying a full order lifecycle creates exactly one analytics record/event.
  * Migration tests asserting trigger function compiles and uses existing tables/columns.
  * Status-transition contract tests between API and DB constraints.

### 6) Optimized Code / Patch (when possible)

* No runtime code patch applied per instruction.
* Suggested pseudo-patches:
  * **Connection safety wrapper**: introduce a shared context manager around `db_pool.getconn()` ensuring `putconn` in all paths.
  * **Analytics idempotency**:
    ```sql
    CREATE UNIQUE INDEX IF NOT EXISTS ux_order_analytics_order_event
      ON order_analytics(order_id, event_type);

    INSERT INTO order_analytics (...)
    VALUES (...)
    ON CONFLICT (order_id, event_type)
    DO UPDATE SET updated_at = NOW();
    ```
  * **State machine alignment**: migrate status enum/check and trigger condition to one terminal state contract used by API + DB.

### ### SECURITY AUDIT: Optimization audit only (no staged code changes)
**Risk Assessment:** High
#### **Findings:**
* **Hardcoded Database Credentials in Source** (Severity: Critical)
* **Location:** `src/web/routes/api_optimized.py`
* **The Exploit:** Source exposure (repo leak, logs, developer machine compromise) reveals static DB credentials (`user='postgres', password='password'`) enabling unauthorized DB access and pivoting.
* **The Fix:** Move credentials to environment/secret manager and fail startup if missing secure values; rotate existing credentials immediately.

* **Missing Authorization on WebSocket Event Handlers** (Severity: High)
* **Location:** `src/web/routes/websocket_kds.py` (`order_ready`, `order_analytics`, `return_all_orders` handlers)
* **The Exploit:** Any connected socket client can emit events to mutate order status and insert analytics without role validation, enabling unauthorized operational tampering and KPI poisoning.
* **The Fix:** Enforce authenticated socket sessions + role-based permission checks before processing state-mutating events.

* **Potential Connection Exhaustion DoS via Exception Paths** (Severity: Medium)
* **Location:** `src/web/routes/api_optimized.py` pooled DB usage paths
* **The Exploit:** Repeated malformed requests triggering exceptions can leak pooled connections if not always returned, causing pool starvation and service degradation.
* **The Fix:** Use `try/finally` or context managers for guaranteed cursor/connection release on every path.

#### **Observations:**
* SQL parameterization is present in several raw cursor executions, which reduces direct SQL injection risk in those specific statements.
* A custom SQL-injection keyword filter exists but should not be treated as a primary defense; rely on parameterized queries and strict schema-based validation.
