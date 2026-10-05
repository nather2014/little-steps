package main

import (
	"context"
	"database/sql"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5"
)

const metricCapacity = 6000
const metricWindow = 15 * time.Minute

type metricSample struct {
	At     time.Time `json:"at"`
	Kind   string    `json:"kind"`
	Route  string    `json:"route"`
	Millis float64   `json:"ms"`
	Status int       `json:"status"`
}
type monitoring struct {
	sync.Mutex
	started           time.Time
	samples           []metricSample
	next              int
	activity          map[string]time.Time
	cpuTotal, cpuIdle uint64
}

func newMonitoring() *monitoring {
	return &monitoring{started: time.Now(), activity: map[string]time.Time{}}
}
func (m *monitoring) record(s metricSample) {
	m.Lock()
	defer m.Unlock()
	if len(m.samples) < metricCapacity {
		m.samples = append(m.samples, s)
	} else {
		m.samples[m.next] = s
		m.next = (m.next + 1) % metricCapacity
	}
}
func (m *monitoring) touch(id string, now time.Time) bool {
	m.Lock()
	defer m.Unlock()
	if now.Sub(m.activity[id]) < time.Minute {
		return false
	}
	if len(m.activity) >= 10000 {
		for k, t := range m.activity {
			if now.Sub(t) > 5*time.Minute {
				delete(m.activity, k)
			}
		}
		if len(m.activity) >= 10000 {
			return false
		}
	}
	m.activity[id] = now
	return true
}
func metricSummary(samples []metricSample) map[string]any {
	values := make([]float64, 0, len(samples))
	errors := 0
	for _, s := range samples {
		values = append(values, s.Millis)
		if s.Status >= 500 {
			errors++
		}
	}
	sort.Float64s(values)
	result := map[string]any{"count": len(values), "server_errors": errors, "p50_ms": nil, "p95_ms": nil}
	if len(values) > 0 {
		result["p50_ms"] = values[(len(values)-1)/2]
		result["p95_ms"] = values[(95*len(values)+99)/100-1]
	}
	return result
}
func (m *monitoring) snapshot(now time.Time) map[string]any {
	m.Lock()
	samples := append([]metricSample(nil), m.samples...)
	started := m.started
	m.Unlock()
	groups := map[string][]metricSample{}
	recent := []metricSample{}
	for _, s := range samples {
		if now.Sub(s.At) > metricWindow {
			continue
		}
		groups[s.Kind] = append(groups[s.Kind], s)
		if s.Kind == "api" && s.Status >= 400 {
			recent = append(recent, s)
		}
	}
	sort.Slice(recent, func(i, j int) bool { return recent[i].At.After(recent[j].At) })
	if len(recent) > 20 {
		recent = recent[:20]
	}
	routes := map[string][]metricSample{}
	for _, s := range groups["api"] {
		routes[s.Route] = append(routes[s.Route], s)
	}
	endpoints := []map[string]any{}
	for route, values := range routes {
		row := metricSummary(values)
		row["route"] = route
		endpoints = append(endpoints, row)
	}
	sort.Slice(endpoints, func(i, j int) bool { return endpoints[i]["count"].(int) > endpoints[j]["count"].(int) })
	return map[string]any{"uptime_seconds": int(now.Sub(started).Seconds()), "window_minutes": 15, "sample_capacity": metricCapacity, "api": metricSummary(groups["api"]), "database_queries": metricSummary(groups["database"]), "page_load": metricSummary(groups["browser"]), "recent_errors": recent, "endpoints": endpoints}
}

type queryTiming struct{ start time.Time }
type queryTimingKey struct{}

func (m *monitoring) TraceQueryStart(ctx context.Context, _ *pgx.Conn, _ pgx.TraceQueryStartData) context.Context {
	return context.WithValue(ctx, queryTimingKey{}, queryTiming{time.Now()})
}
func (m *monitoring) TraceQueryEnd(ctx context.Context, _ *pgx.Conn, data pgx.TraceQueryEndData) {
	t, ok := ctx.Value(queryTimingKey{}).(queryTiming)
	if !ok {
		return
	}
	status := 200
	if data.Err != nil {
		status = 500
	}
	m.record(metricSample{At: time.Now(), Kind: "database", Millis: float64(time.Since(t.start).Microseconds()) / 1000, Status: status})
}

type statusWriter struct {
	http.ResponseWriter
	status int
}

func (w *statusWriter) WriteHeader(status int) {
	if w.status == 0 {
		w.status = status
		w.ResponseWriter.WriteHeader(status)
	}
}
func (w *statusWriter) Write(p []byte) (int, error) {
	if w.status == 0 {
		w.WriteHeader(200)
	}
	return w.ResponseWriter.Write(p)
}
func (w *statusWriter) Unwrap() http.ResponseWriter { return w.ResponseWriter }
func monitoredRoute(path string) string {
	switch path {
	case "/api/profile", "/api/children", "/api/attempts", "/api/comparisons", "/api/time_trials", "/api/learning", "/api/lesson", "/api/rewards", "/api/parents", "/api/auth/me", "/api/auth/login", "/api/auth/register", "/api/auth/logout", "/api/auth/guest":
		return path
	}
	if strings.HasPrefix(path, "/api/rpc/") {
		switch strings.TrimPrefix(path, "/api/rpc/") {
		case "available_exams", "start_exam", "submit_exam", "save_answers", "not_studied", "targeted_practice", "mistake_note", "curriculum", "leaderboard", "create_link_code", "link_child", "unlink_parent", "setup_profile", "start_time_trial", "answer_time_trial", "resume_time_trial", "finish_time_trial":
			return path
		}
	}
	return "/api/other"
}
func (m *monitoring) wrap(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !strings.HasPrefix(r.URL.Path, "/api/") || r.URL.Path == "/api/health" || r.URL.Path == "/api/activity" || r.URL.Path == "/api/telemetry" || strings.HasPrefix(r.URL.Path, "/api/admin/") {
			next.ServeHTTP(w, r)
			return
		}
		start := time.Now()
		sw := &statusWriter{ResponseWriter: w}
		next.ServeHTTP(sw, r)
		if sw.status == 0 {
			sw.status = 200
		}
		ms := float64(time.Since(start).Microseconds()) / 1000
		route := monitoredRoute(r.URL.Path)
		m.record(metricSample{At: time.Now(), Kind: "api", Route: route, Millis: ms, Status: sw.status})
		if sw.status >= 500 || ms >= 1000 {
			slog.Info("http_request", "method", r.Method, "route", route, "status", sw.status, "duration_ms", ms)
		}
	})
}

func readKeyValues(path string) map[string]uint64 {
	b, e := os.ReadFile(path)
	out := map[string]uint64{}
	if e != nil {
		return out
	}
	for _, line := range strings.Split(string(b), "\n") {
		f := strings.Fields(line)
		if len(f) >= 2 {
			v, e := strconv.ParseUint(f[1], 10, 64)
			if e == nil {
				out[strings.TrimSuffix(f[0], ":")] = v
			}
		}
	}
	return out
}
func (m *monitoring) systemMetrics() map[string]any {
	out := map[string]any{"cpu_percent": nil}
	mem := readKeyValues("/proc/meminfo")
	if total := mem["MemTotal"]; total > 0 {
		available := mem["MemAvailable"]
		out["memory_total_bytes"] = total * 1024
		out["memory_used_bytes"] = (total - available) * 1024
		out["memory_source"] = "Linux memory statistics"
	}
	current, e := os.ReadFile("/sys/fs/cgroup/memory.current")
	limit, e2 := os.ReadFile("/sys/fs/cgroup/memory.max")
	if e == nil && e2 == nil {
		used, eu := strconv.ParseUint(strings.TrimSpace(string(current)), 10, 64)
		total, et := strconv.ParseUint(strings.TrimSpace(string(limit)), 10, 64)
		if eu == nil && et == nil && total > 0 {
			out["memory_total_bytes"] = total
			out["memory_used_bytes"] = used
			out["memory_source"] = "Container memory limit"
		}
	}
	if raw, e := os.ReadFile("/proc/stat"); e == nil {
		f := strings.Fields(strings.SplitN(string(raw), "\n", 2)[0])
		if len(f) >= 5 {
			var total, idle uint64
			for i := 1; i < len(f) && i <= 8; i++ {
				v, _ := strconv.ParseUint(f[i], 10, 64)
				total += v
				if i == 4 || i == 5 {
					idle += v
				}
			}
			m.Lock()
			if total > m.cpuTotal && m.cpuTotal > 0 && idle >= m.cpuIdle {
				out["cpu_percent"] = 100 * (1 - float64(idle-m.cpuIdle)/float64(total-m.cpuTotal))
			}
			m.cpuTotal, m.cpuIdle = total, idle
			m.Unlock()
		}
	}
	self := readKeyValues("/proc/self/status")
	out["go_rss_bytes"] = self["VmRSS"] * 1024
	var stats runtime.MemStats
	runtime.ReadMemStats(&stats)
	out["go_heap_bytes"] = stats.HeapAlloc
	out["goroutines"] = runtime.NumGoroutine()
	out["cpu_source"] = "Linux CPU statistics; interval between refreshes"
	var disk syscall.Statfs_t
	if syscall.Statfs(".", &disk) == nil {
		out["disk_total_bytes"] = disk.Blocks * uint64(disk.Bsize)
		out["disk_available_bytes"] = disk.Bavail * uint64(disk.Bsize)
	}
	return out
}
func (a *app) adminMetrics(ctx context.Context, p actor) (any, error) {
	var allowed bool
	if e := a.db.QueryRowContext(ctx, "SELECT is_admin FROM users WHERE id=$1", p.ID).Scan(&allowed); e != nil {
		return nil, e
	}
	if !allowed {
		return nil, forbidden()
	}
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	now := time.Now()
	day, end, _, _ := learningPeriods(now)
	var total, guests, online, daily, matches, normal, ranked, olympiad, trials int
	query := `SELECT (SELECT count(*) FROM users),(SELECT count(*) FROM users WHERE is_guest),(SELECT count(*) FROM users WHERE last_active_at>=now()-interval '5 minutes'),(SELECT count(*) FROM users WHERE last_active_at >= $1 AND last_active_at < $2),(SELECT count(*) FROM attempts WHERE submitted_at >= $1 AND submitted_at < $2),count(*) FILTER(WHERE s.mode='practice'),count(*) FILTER(WHERE s.mode IN ('weekly','ranked') AND e.subject NOT LIKE 'olympiad_%'),count(*) FILTER(WHERE s.mode IN ('weekly','ranked') AND e.subject LIKE 'olympiad_%'),count(*) FILTER(WHERE s.mode='time_trial') FROM exam_sessions s JOIN exams e ON e.id=s.exam_id WHERE NOT s.submitted AND COALESCE(s.deadline_at,s.started_at+interval '2 hours')>now()`
	if e := a.db.QueryRowContext(ctx, query, day, end).Scan(&total, &guests, &online, &daily, &matches, &normal, &ranked, &olympiad, &trials); e != nil {
		return nil, e
	}
	var size int64
	var connections int
	var hit, read int64
	if e := a.db.QueryRowContext(ctx, "SELECT pg_database_size(current_database()),numbackends,blks_hit,blks_read FROM pg_stat_database WHERE datname=current_database()").Scan(&size, &connections, &hit, &read); e != nil {
		return nil, e
	}
	pool := a.db.Stats()
	result := a.monitor.snapshot(now)
	result["sampled_at"] = now
	result["usage"] = map[string]any{"total_users": total, "guest_users": guests, "online_users": online, "daily_active_users": daily, "matches_today": matches, "active_matches": normal + ranked + olympiad + trials, "normal": normal, "ranked": ranked, "olympiad": olympiad, "time_trials": trials, "day_timezone": "Asia/Kolkata"}
	result["system"] = a.monitor.systemMetrics()
	var ratio any
	if hit+read > 0 {
		ratio = 100 * float64(hit) / float64(hit+read)
	}
	result["database"] = map[string]any{"size_bytes": size, "connections": connections, "cache_hit_percent": ratio, "pool_open": pool.OpenConnections, "pool_in_use": pool.InUse, "pool_limit": pool.MaxOpenConnections, "pool_wait_count": pool.WaitCount}
	return result, nil
}
func (a *app) browserTiming(w http.ResponseWriter, r *http.Request) error {
	var payload struct {
		LoadMS float64 `json:"load_ms"`
	}
	if e := decode(w, r, &payload); e != nil {
		return e
	}
	if payload.LoadMS <= 0 || payload.LoadMS > 120000 {
		return bad("Invalid page timing")
	}
	a.monitor.record(metricSample{At: time.Now(), Kind: "browser", Millis: payload.LoadMS, Status: 200})
	writeJSON(w, 200, map[string]bool{"ok": true})
	return nil
}
func setAdmin(ctx context.Context, db *sql.DB, identifier string, enabled bool) error {
	res, e := db.ExecContext(ctx, "UPDATE users SET is_admin=$2 WHERE id=$1 OR lower(email)=lower($1)", strings.TrimSpace(identifier), enabled)
	if e != nil {
		return e
	}
	n, e := res.RowsAffected()
	if e == nil && n != 1 {
		return fmt.Errorf("Expected one existing account, found %d", n)
	}
	return e
}
