# Private monitoring

Monitoring runs in the existing Go process, without a separate metrics server or paid service. The Admin tab appears only for accounts whose users.is_admin flag was granted by the server operator. Every metrics request checks that flag; students, parents and anonymous users otherwise receive 403/401. No signup/profile RPC can grant admin privileges.

The dashboard refreshes every 30 seconds while visible. It shows recent online accounts (activity within five minutes), unfinished/unexpired matches by mode, daily active accounts, completed attempts today, total/guest accounts, RAM, CPU, filesystem space, Go process memory, PostgreSQL size/connections/cache hit rate, connection-pool utilization, API/database/browser load p50/p95 and recent failed API requests.

Visible authenticated pages send a heartbeat each minute. Last activity is persisted at most once per account per minute. Online counts are estimates. Daily counts use Asia/Kolkata. Expired match timers are excluded even when the learner has not reopened the round.

A pgx query tracer records execution duration and error status without SQL text or arguments. API route labels are restricted to known routes; URLs, query strings, headers, cookies, names and answers are not logged by monitoring. Failed API requests and requests over one second generate structured request fields in systemd logs. Existing detailed application exceptions remain server-side.

Latency samples use a rolling 15-minute window and a shared maximum of 6,000 samples. Recent errors are limited to 20. Timing data and CPU baselines reset on restart; user activity persists. Browser timing measures navigation through the load event, not every later SPA action. CPU/disk measurements may include shared-host values on container-based VPSs; memory uses a container limit when available and Linux memory statistics otherwise. No external uptime checks or alert notifications are configured in this version.

## Operator access

Inside Docker: `docker compose exec app ./little-steps grant-admin EMAIL_OR_USER_ID`. Revoke with `revoke-admin`. For the native VPS installation, run the same binary with its existing DATABASE_URL environment, for example through systemd-run with EnvironmentFile=/etc/little-steps.env and User=little-steps. Never put a database password in a browser or URL. Prefer a registered account so admin access survives browser-cookie loss.

Checks: Go unit tests/vet, scripts/test-monitoring.py and scripts/test-monitoring-browser.cjs. Test grants are local-only; live verification uses an explicitly created temporary guest that is removed afterwards.
