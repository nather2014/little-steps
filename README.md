# Little Steps

Plain HTML/CSS/JavaScript → Go API → PostgreSQL. The Go server serves the frontend and API from the same origin.

## Project files

- `web/`: current frontend.
- `backend/`: Go API, unit tests, embedded question banks and PostgreSQL schema.
- `scripts/`: question generators, current integration/browser checks and local database backup helper.
- `deploy/`: native Ubuntu VPS installation helpers.
- `Dockerfile` and `compose.yaml`: local app and PostgreSQL environment.
- `.tools/`: local Go and browser testing tools; not deployed.
- `backups/`: protected local database backups; not deployed.

Retired prototypes, deployment alternatives, screenshots and obsolete tests are archived outside this project in `../little-steps-archives/`.

## Run locally

```bash
cp -n .env.example .env
# Set DATABASE_PASSWORD to a long random hex value in .env.
docker compose up -d --build
```

Open http://localhost:8090. Create a student or parent account, or continue as a guest. Never commit `.env`. Do not run `docker compose down -v` against a database you want to keep.

## Current behavior

Students have four dashboard modes: **Normal**, **Ranked**, **Olympiad Ranked**, and **Time Trials**. Ranked tests have ten questions, server-managed timers, unlimited attempts, and positive/negative RR. Normal provides topic practice without RR. Career shows chronological match history, mode filters, stats, answer review and private score comparisons where enough other learners exist. Daily/weekly missions are retired. The student dashboard shows rank and RR; historical match XP and parent progress remain available.

LKG, UKG and Classes 1–10 remain available. Class 2 has 939 question entries: Maths 314, English 248, The World Around Us 90, Olympiad Maths 164 and Olympiad Reasoning 123. Questions and grading remain server-side. “Not studied yet” replaces eligible questions and saves unstudied topics. See [curriculum scope](CURRICULUM.md) and [exam/reward rules](GAMIFICATION.md).

Parents link a child using a 15-minute, single-use code. They can view only linked children's results and progress. Children can revoke access. Admin monitoring is separately granted by the server operator; see [monitoring](MONITORING.md).

Guest accounts require no email or phone. Their browser session lasts 30 days. Logout, cookie deletion, expiry or another browser loses access; guest recovery/conversion is not implemented. Registered sessions last 24 hours. Email verification and automatic password-reset emails are not implemented.

## Native VPS deployment

The live site is https://littlesteps.space. It uses the native Go systemd service, PostgreSQL and Nginx. Runtime files are in `/opt/little-steps`; protected configuration is `/etc/little-steps.env`. Provider routing forwards the public domain to Nginx on the NAT VPS.

`deploy/install-native.sh` is a fresh-server Ubuntu installer. It expects a compiled `backend/little-steps` binary and `APP_ORIGIN` set to the public URL. `deploy/finalize-native.py` handles the native installation's database-encoding and Nginx finalization. Review these installers before using them on an existing deployment.

Build a release binary:

```bash
cd backend
CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o little-steps .
```

For updates, back up first, install the compiled binary and current `web/` into `/opt/little-steps`, then restart `little-steps`. Do not overwrite the existing environment or database. Check `/api/health` and the service logs:

```bash
systemctl status little-steps
journalctl -u little-steps --no-pager -n 100
```

Password recovery is an operator action. After verifying the account owner, run the binary's `reset-password EMAIL` command with the existing database environment and pass the new password through standard input. This revokes that user's sessions. Role/class changes are operator actions.

## Backups

Native VPS backups run daily at 02:15 server time in `/var/backups/little-steps`. Run `/usr/local/sbin/little-steps-backup` for an immediate backup and keep an off-server copy.

For the local Docker database, `bash scripts/backup.sh` writes a restricted dump into `backups/`. Validate without changing data:

```bash
docker compose exec -T db pg_restore --list < backups/YOUR_BACKUP.dump
```

Restore into a fresh database and inspect it before switching the app connection. A persistent Docker volume is not a backup against machine loss.

## Checks

```bash
cd backend
go test ./...
go vet ./...
cd ..
node scripts/test-analytics.cjs
python3 scripts/test-api.py
python3 scripts/test-class2-bank.py
```

Integration checks create accounts and attempts: use a local installation. Other current API checks cover curriculum, timers, rewards, learning, time trials and monitoring. Current browser checks are `test-career-browser.cjs`, `test-learning-browser.cjs`, `test-trials-browser.cjs`, and `test-monitoring-browser.cjs` in `scripts/`. They use Playwright with Chromium; set `PLAYWRIGHT_MODULE` and `PLAYWRIGHT_BROWSERS_PATH` to the installed tools if necessary. Privileged monitoring checks are local-only.
