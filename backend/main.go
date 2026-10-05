package main

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"embed"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/mail"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"
	"unicode/utf8"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/stdlib"
	"golang.org/x/crypto/bcrypt"
)

//go:embed data/*
var dataFiles embed.FS

type app struct {
	monitor *monitoring
	db      *sql.DB
	bank    map[string][]subject
	origin  string
	secure  bool
	limiter *rateLimiter
}
type subject struct {
	ID        string            `json:"id"`
	Name      string            `json:"name"`
	Topic     string            `json:"topic"`
	Questions []json.RawMessage `json:"questions"`
	Sources   []string          `json:"sources"`
}
type profile struct {
	ID    string `json:"id"`
	Name  string `json:"display_name"`
	Role  string `json:"role"`
	Grade *int   `json:"grade"`
}
type actor struct {
	ID      string
	Profile *profile
}
type exam struct {
	ID              int64  `json:"id"`
	Grade           int    `json:"grade"`
	Subject         string `json:"subject"`
	Title           string `json:"title"`
	Topic           string `json:"topic"`
	Week            string `json:"week_start"`
	Category        string `json:"category"`
	QuestionCount   int    `json:"question_count"`
	DurationSeconds int    `json:"duration_seconds"`
}
type question struct {
	Prompt      string   `json:"prompt"`
	Options     []string `json:"options"`
	Answer      int      `json:"-"`
	Topic       string   `json:"topic"`
	Difficulty  string   `json:"difficulty,omitempty"`
	Explanation string   `json:"-"`
}
type review struct {
	Prompt      string `json:"prompt"`
	Topic       string `json:"topic"`
	Selected    string `json:"selected"`
	Answer      string `json:"answer"`
	Correct     bool   `json:"correct"`
	Explanation string `json:"explanation,omitempty"`
}
type unseenTopic struct {
	Prompt string `json:"prompt"`
	Topic  string `json:"topic"`
}
type attempt struct {
	ID         int64         `json:"id"`
	Session    string        `json:"session_id"`
	Student    string        `json:"student_id"`
	Exam       int64         `json:"exam_id"`
	Grade      int           `json:"grade"`
	Subject    string        `json:"subject"`
	Week       string        `json:"week_start"`
	Mode       string        `json:"mode"`
	Correct    int           `json:"correct"`
	Total      int           `json:"total"`
	Seconds    int           `json:"seconds"`
	Date       time.Time     `json:"submitted_at"`
	Review     []review      `json:"review"`
	NotStudied []unseenTopic `json:"not_studied"`
	XPEarned   int           `json:"xp_earned"`
	RRDelta    int           `json:"rr_delta"`
}
type apiError struct {
	Status  int
	Message string
}

func (e apiError) Error() string { return e.Message }
func bad(message string) error   { return apiError{400, message} }
func forbidden() error           { return apiError{403, "You don’t have access to this learning space"} }
func randomID() string {
	b := make([]byte, 16)
	if _, e := rand.Read(b); e != nil {
		panic(e)
	}
	return hex.EncodeToString(b)
}
func hash(s string) string { b := sha256.Sum256([]byte(s)); return hex.EncodeToString(b[:]) }
func env(name, fallback string) string {
	if v := os.Getenv(name); v != "" {
		return v
	}
	return fallback
}
func weekStart(t time.Time) string {
	loc, _ := time.LoadLocation("Asia/Kolkata")
	t = t.In(loc)
	t = t.AddDate(0, 0, -(int(t.Weekday())+6)%7)
	return t.Format("2006-01-02")
}

func main() {
	monitor := newMonitoring()
	config, e := pgx.ParseConfig(env("DATABASE_URL", "postgres://little_steps:local-development-only@localhost:5433/little_steps?sslmode=disable"))
	if e != nil {
		log.Fatal("Invalid database configuration")
	}
	config.Tracer = monitor
	db := stdlib.OpenDB(*config)
	defer db.Close()
	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(30 * time.Minute)
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if e = db.PingContext(ctx); e != nil {
		log.Fatal("PostgreSQL is unavailable: ", e)
	}
	if e = migrate(ctx, db); e != nil {
		log.Fatal("Database migration failed: ", e)
	}
	if len(os.Args) > 1 {
		if len(os.Args) != 3 {
			log.Fatal("Usage: little-steps reset-password|grant-admin|revoke-admin EMAIL_OR_ID")
		}
		switch os.Args[1] {
		case "reset-password":
			e = resetPassword(ctx, db, os.Args[2], os.Stdin)
		case "grant-admin":
			e = setAdmin(ctx, db, os.Args[2], true)
		case "revoke-admin":
			e = setAdmin(ctx, db, os.Args[2], false)
		default:
			log.Fatal("Unknown operator command")
		}
		if e != nil {
			log.Fatal(e)
		}
		log.Print("Operator command completed")
		return
	}
	raw, e := dataFiles.ReadFile("data/curriculum.json")
	if e != nil {
		log.Fatal(e)
	}
	a := &app{db: db, monitor: monitor, origin: env("APP_ORIGIN", "http://localhost:8090"), secure: env("SECURE_COOKIES", "false") == "true", limiter: newRateLimiter()}
	if e = json.Unmarshal(raw, &a.bank); e != nil {
		log.Fatal(e)
	}
	challengeRaw, err := dataFiles.ReadFile("data/olympiad.json")
	if err != nil {
		log.Fatal(err)
	}
	var challenges map[string][]subject
	if err = json.Unmarshal(challengeRaw, &challenges); err != nil {
		log.Fatal(err)
	}
	for grade, subjects := range challenges {
		a.bank[grade] = append(a.bank[grade], subjects...)
	}

	addBorrowingSkills(a.bank)
	server := &http.Server{Addr: env("LISTEN_ADDR", "127.0.0.1:8090"), Handler: a.routes(env("WEB_DIR", "../web")), ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 30 * time.Second, IdleTimeout: 60 * time.Second}
	done := make(chan os.Signal, 1)
	signal.Notify(done, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-done
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		server.Shutdown(ctx)
	}()
	log.Printf("Little Steps listening on %s", server.Addr)
	if e = server.ListenAndServe(); e != nil && !errors.Is(e, http.ErrServerClosed) {
		log.Fatal(e)
	}
}
func migrate(ctx context.Context, db *sql.DB) error {
	tx, e := db.BeginTx(ctx, nil)
	if e != nil {
		return e
	}
	defer tx.Rollback()
	if _, e = tx.ExecContext(ctx, "SELECT pg_advisory_xact_lock(721836401)"); e != nil {
		return e
	}
	raw, e := dataFiles.ReadFile("data/schema.sql")
	if e != nil {
		return e
	}
	if _, e = tx.ExecContext(ctx, string(raw)); e != nil {
		return e
	}
	return tx.Commit()
}
func (a *app) routes(webDir string) http.Handler {
	if a.monitor == nil {
		a.monitor = newMonitoring()
	}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/health", func(w http.ResponseWriter, r *http.Request) {
		ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
		defer cancel()
		if a.db.PingContext(ctx) != nil {
			writeJSON(w, 503, map[string]string{"status": "unavailable"})
			return
		}
		writeJSON(w, 200, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("/api/", a.serveAPI)
	files := http.FileServer(http.Dir(webDir))
	mux.Handle("/", files)
	return a.monitor.wrap(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("Referrer-Policy", "same-origin")
		w.Header().Set("X-Frame-Options", "DENY")
		w.Header().Set("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
		if strings.HasPrefix(r.URL.Path, "/api/") {
			w.Header().Set("Cache-Control", "no-store")
		}
		if r.Method != "GET" && r.Method != "HEAD" {
			if r.Header.Get("Origin") != a.origin || r.Header.Get("X-Little-Steps") != "1" || !strings.HasPrefix(r.Header.Get("Content-Type"), "application/json") {
				writeJSON(w, 403, map[string]string{"error": "Request origin could not be verified"})
				return
			}
		}
		mux.ServeHTTP(w, r)
	}))
}
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
func decode(w http.ResponseWriter, r *http.Request, v any) error {
	r.Body = http.MaxBytesReader(w, r.Body, 16384)
	d := json.NewDecoder(r.Body)
	d.DisallowUnknownFields()
	if d.Decode(v) != nil {
		return bad("Please check the submitted fields")
	}
	var extra any
	if d.Decode(&extra) != io.EOF {
		return bad("Invalid request body")
	}
	return nil
}
func fail(w http.ResponseWriter, e error) {
	var ae apiError
	if errors.As(e, &ae) {
		writeJSON(w, ae.Status, map[string]string{"error": ae.Message})
		return
	}
	log.Printf("API error: %v", e)
	writeJSON(w, 500, map[string]string{"error": "Something went wrong. Please try again"})
}
func (a *app) serveAPI(w http.ResponseWriter, r *http.Request) {
	if strings.HasPrefix(r.URL.Path, "/api/auth/") {
		if e := a.auth(w, r); e != nil {
			fail(w, e)
		}
		return
	}
	person, e := a.authenticate(r)
	if e != nil {
		fail(w, e)
		return
	}
	if r.Method == "POST" && r.URL.Path == "/api/telemetry" {
		if e := a.browserTiming(w, r); e != nil {
			fail(w, e)
		}
		return
	}
	if r.Method == "GET" {
		var result any
		switch r.URL.Path {
		case "/api/admin/metrics":
			result, e = a.adminMetrics(r.Context(), person)
		case "/api/activity":
			result = map[string]bool{"ok": true}
		case "/api/profile":
			result = person.Profile
		case "/api/children":
			result, e = a.children(r.Context(), person)
		case "/api/attempts":
			result, e = a.history(r.Context(), person, r.URL.Query().Get("student_id"))
		case "/api/comparisons":
			result, e = a.comparisons(r.Context(), person, r.URL.Query().Get("student_id"))
		case "/api/time_trials":
			result, e = a.trialHistory(r.Context(), person, r.URL.Query().Get("student_id"))
		case "/api/learning":
			result, e = a.learning(r.Context(), person, r.URL.Query().Get("student_id"))
		case "/api/lesson":
			result, e = a.lesson(r.Context(), person, r.URL.Query().Get("student_id"), r.URL.Query().Get("subject"), r.URL.Query().Get("topic"))
		case "/api/rewards":
			result, e = a.rewards(r.Context(), person, r.URL.Query().Get("student_id"), time.Now())
		case "/api/parents":
			result, e = a.parents(r.Context(), person)
		default:
			e = apiError{404, "Page not found"}
		}
		if e != nil {
			fail(w, e)
		} else {
			writeJSON(w, 200, result)
		}
		return
	}
	if r.Method != "POST" {
		fail(w, apiError{405, "Method not allowed"})
		return
	}
	result, e := a.rpc(w, r, person)
	if e != nil {
		fail(w, e)
	} else {
		writeJSON(w, 200, result)
	}
}
func (a *app) authenticate(r *http.Request) (actor, error) {
	c, e := r.Cookie("little_steps_session")
	if e != nil {
		return actor{}, apiError{401, "Please sign in"}
	}
	var p actor
	e = a.db.QueryRowContext(r.Context(), "SELECT user_id FROM auth_sessions WHERE token_hash=$1 AND expires_at>now()", hash(c.Value)).Scan(&p.ID)
	if errors.Is(e, sql.ErrNoRows) {
		return p, apiError{401, "Please sign in"}
	}
	if e != nil {
		return p, e
	}
	pr := profile{}
	e = a.db.QueryRowContext(r.Context(), "SELECT id,display_name,role,grade FROM profiles WHERE id=$1", p.ID).Scan(&pr.ID, &pr.Name, &pr.Role, &pr.Grade)
	if e == nil {
		p.Profile = &pr
	} else if !errors.Is(e, sql.ErrNoRows) {
		return p, e
	}
	if a.monitor != nil && a.monitor.touch(p.ID, time.Now()) {
		if _, e := a.db.ExecContext(r.Context(), "UPDATE users SET last_active_at=now() WHERE id=$1", p.ID); e != nil {
			log.Print("Activity update failed")
		}
	}
	return p, nil
}
func (a *app) auth(w http.ResponseWriter, r *http.Request) error {
	if r.URL.Path == "/api/auth/me" && r.Method == "GET" {
		p, e := a.authenticate(r)
		if e != nil {
			return e
		}
		var guest, admin bool
		if e := a.db.QueryRowContext(r.Context(), "SELECT is_guest,is_admin FROM users WHERE id=$1", p.ID).Scan(&guest, &admin); e != nil {
			return e
		}
		writeJSON(w, 200, map[string]any{"user": map[string]any{"id": p.ID, "is_guest": guest, "is_admin": admin}})
		return nil
	}
	if r.Method != "POST" {
		return apiError{405, "Method not allowed"}
	}
	if r.URL.Path == "/api/auth/logout" {
		if c, e := r.Cookie("little_steps_session"); e == nil {
			if _, e = a.db.ExecContext(r.Context(), "DELETE FROM auth_sessions WHERE token_hash=$1", hash(c.Value)); e != nil {
				return e
			}
		}
		a.cookie(w, "", -1)
		writeJSON(w, 200, map[string]any{})
		return nil
	}
	if r.URL.Path != "/api/auth/login" && r.URL.Path != "/api/auth/register" && r.URL.Path != "/api/auth/guest" {
		return apiError{404, "Page not found"}
	}
	host, _, _ := net.SplitHostPort(r.RemoteAddr)
	if !a.limiter.allow(host, time.Now()) {
		return apiError{429, "Too many login attempts. Please try again in ten minutes"}
	}
	var input struct {
		Email    string `json:"email"`
		Password string `json:"password"`
	}
	if e := decode(w, r, &input); e != nil {
		return e
	}
	guest := r.URL.Path == "/api/auth/guest"
	var id string
	if guest {
		id = randomID()
	} else {
		email := strings.ToLower(strings.TrimSpace(input.Email))
		parsed, e := mail.ParseAddress(email)
		if e != nil || parsed.Address != email || len(email) > 254 || len(input.Password) < 8 || len(input.Password) > 72 {
			return bad("Enter a valid email and a password of 8–72 bytes")
		}
		if r.URL.Path == "/api/auth/register" {
			hashed, e := bcrypt.GenerateFromPassword([]byte(input.Password), bcrypt.DefaultCost)
			if e != nil {
				return e
			}
			id = randomID()
			_, e = a.db.ExecContext(r.Context(), "INSERT INTO users(id,email,password_hash) VALUES($1,$2,$3)", id, email, string(hashed))
			if e != nil {
				var pg *pgconn.PgError
				if errors.As(e, &pg) && pg.Code == "23505" {
					return apiError{409, "An account with this email already exists. Please sign in"}
				}
				return e
			}
		}
		if r.URL.Path == "/api/auth/login" {
			var hashed string
			e = a.db.QueryRowContext(r.Context(), "SELECT id,password_hash FROM users WHERE email=$1", email).Scan(&id, &hashed)
			if e != nil && !errors.Is(e, sql.ErrNoRows) {
				return e
			}
			if errors.Is(e, sql.ErrNoRows) {
				hashed = "$2a$10$7EqJtq98hPqEX7fNZaFWoO5o.W5Cy6LhmxREdqNyZvPfMPb1mqJTu"
			}
			passwordError := bcrypt.CompareHashAndPassword([]byte(hashed), []byte(input.Password))
			if e != nil || passwordError != nil {
				return apiError{401, "Email or password is incorrect"}
			}
		}
	}
	token := randomID() + randomID()
	tx, e := a.db.BeginTx(r.Context(), nil)
	if e != nil {
		return e
	}
	defer tx.Rollback()
	maxAge := 86400
	if guest {
		maxAge = 30 * 86400
		if _, e = tx.ExecContext(r.Context(), "INSERT INTO users(id,is_guest) VALUES($1,true)", id); e != nil {
			return e
		}
	}
	if c, e := r.Cookie("little_steps_session"); e == nil {
		if _, e = tx.ExecContext(r.Context(), "DELETE FROM auth_sessions WHERE token_hash=$1", hash(c.Value)); e != nil {
			return e
		}
	}
	if _, e = tx.ExecContext(r.Context(), "DELETE FROM auth_sessions WHERE expires_at<now()"); e != nil {
		return e
	}
	if _, e = tx.ExecContext(r.Context(), "INSERT INTO auth_sessions(token_hash,user_id,expires_at) VALUES($1,$2,now()+$3 * interval '1 second')", hash(token), id, maxAge); e != nil {
		return e
	}
	if e = tx.Commit(); e != nil {
		return e
	}
	a.cookie(w, token, maxAge)
	writeJSON(w, 200, map[string]any{"user": map[string]any{"id": id, "is_guest": guest}, "session": true})
	return nil
}
func (a *app) cookie(w http.ResponseWriter, value string, maxAge int) {
	http.SetCookie(w, &http.Cookie{Name: "little_steps_session", Value: value, Path: "/", MaxAge: maxAge, HttpOnly: true, Secure: a.secure, SameSite: http.SameSiteLaxMode})
}
func student(p actor) error {
	if p.Profile == nil || p.Profile.Role != "student" {
		return forbidden()
	}
	return nil
}
func (a *app) canRead(ctx context.Context, p actor, id string) error {
	if p.ID == id && p.Profile != nil && p.Profile.Role == "student" {
		return nil
	}
	if p.Profile == nil || p.Profile.Role != "parent" {
		return forbidden()
	}
	var allowed bool
	if e := a.db.QueryRowContext(ctx, "SELECT EXISTS(SELECT 1 FROM parent_children WHERE parent_id=$1 AND child_id=$2)", p.ID, id).Scan(&allowed); e != nil {
		return e
	}
	if !allowed {
		return forbidden()
	}
	return nil
}
func (a *app) children(ctx context.Context, p actor) ([]profile, error) {
	if p.Profile == nil || p.Profile.Role != "parent" {
		return nil, forbidden()
	}
	rows, e := a.db.QueryContext(ctx, "SELECT p.id,p.display_name,p.role,p.grade FROM profiles p JOIN parent_children l ON p.id=l.child_id WHERE l.parent_id=$1 ORDER BY p.display_name", p.ID)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	result := []profile{}
	for rows.Next() {
		var pr profile
		if e = rows.Scan(&pr.ID, &pr.Name, &pr.Role, &pr.Grade); e != nil {
			return nil, e
		}
		result = append(result, pr)
	}
	return result, rows.Err()
}
func (a *app) parents(ctx context.Context, p actor) ([]map[string]string, error) {
	if e := student(p); e != nil {
		return nil, e
	}
	rows, e := a.db.QueryContext(ctx, "SELECT p.id,p.display_name FROM profiles p JOIN parent_children l ON l.parent_id=p.id WHERE l.child_id=$1", p.ID)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	result := []map[string]string{}
	for rows.Next() {
		var id, name string
		if e = rows.Scan(&id, &name); e != nil {
			return nil, e
		}
		result = append(result, map[string]string{"parent_id": id, "display_name": name})
	}
	return result, rows.Err()
}

const attemptColumns = "id,session_id,student_id,exam_id,grade,subject,week_start::text,mode,correct,total,seconds,submitted_at,review,not_studied,xp_earned,rr_delta"

type scanner interface{ Scan(...any) error }

func scanAttempt(row scanner) (attempt, error) {
	var v attempt
	var raw, unseen []byte
	e := row.Scan(&v.ID, &v.Session, &v.Student, &v.Exam, &v.Grade, &v.Subject, &v.Week, &v.Mode, &v.Correct, &v.Total, &v.Seconds, &v.Date, &raw, &unseen, &v.XPEarned, &v.RRDelta)
	if e == nil {
		e = json.Unmarshal(raw, &v.Review)
		if e == nil {
			e = json.Unmarshal(unseen, &v.NotStudied)
		}
	}
	return v, e
}
func (a *app) history(ctx context.Context, p actor, id string) ([]attempt, error) {
	if id == "" {
		id = p.ID
	}
	if e := a.canRead(ctx, p, id); e != nil {
		return nil, e
	}
	rows, e := a.db.QueryContext(ctx, "SELECT "+attemptColumns+" FROM attempts WHERE student_id=$1 ORDER BY submitted_at DESC", id)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	result := []attempt{}
	for rows.Next() {
		v, e := scanAttempt(rows)
		if e != nil {
			return nil, e
		}
		result = append(result, v)
	}
	return result, rows.Err()
}

func (a *app) rpc(w http.ResponseWriter, r *http.Request, p actor) (any, error) {
	ctx := r.Context()
	switch r.URL.Path {
	case "/api/rpc/setup_profile":
		var input struct {
			Name  string `json:"p_name"`
			Role  string `json:"p_role"`
			Grade *int   `json:"p_grade"`
		}
		if e := decode(w, r, &input); e != nil {
			return nil, e
		}
		name := strings.TrimSpace(input.Name)
		if utf8.RuneCountInString(name) < 1 || utf8.RuneCountInString(name) > 60 || (input.Role != "parent" && input.Role != "student") || (input.Role == "parent" && input.Grade != nil) || (input.Role == "student" && (input.Grade == nil || *input.Grade < -1 || *input.Grade > 10)) {
			return nil, bad("Enter a name, role, and valid student class")
		}
		if p.Profile != nil {
			return nil, apiError{409, "Your profile is already set up"}
		}
		_, e := a.db.ExecContext(ctx, "INSERT INTO profiles(id,display_name,role,grade) VALUES($1,$2,$3,$4)", p.ID, name, input.Role, input.Grade)
		return map[string]any{}, e
	case "/api/rpc/available_exams":
		return a.availableExams(ctx, p)
	case "/api/rpc/start_exam":
		var input struct {
			Exam int64  `json:"p_exam"`
			Mode string `json:"p_mode"`
		}
		if e := decode(w, r, &input); e != nil {
			return nil, e
		}
		return a.startExam(ctx, p, input.Exam, input.Mode)
	case "/api/rpc/submit_exam":
		var input struct {
			Session string `json:"p_session"`
			Answers []*int `json:"p_answers"`
		}
		if e := decode(w, r, &input); e != nil {
			return nil, e
		}
		return a.submitExam(ctx, p, input.Session, input.Answers)
	case "/api/rpc/start_time_trial":
		var input struct {
			Exam    int64 `json:"p_exam"`
			Seconds int   `json:"p_seconds"`
		}
		if e := decode(w, r, &input); e != nil {
			return nil, e
		}
		return a.startTrial(ctx, p, input.Exam, input.Seconds)
	case "/api/rpc/resume_time_trial":
		var input struct {
			Session string `json:"p_session"`
		}
		if e := decode(w, r, &input); e != nil {
			return nil, e
		}
		return a.trialAction(ctx, p, input.Session, -1, nil, false)
	case "/api/rpc/answer_time_trial":
		var input struct {
			Session string `json:"p_session"`
			Index   int    `json:"p_index"`
			Answer  *int   `json:"p_answer"`
		}
		if e := decode(w, r, &input); e != nil {
			return nil, e
		}
		if input.Index < 0 {
			return nil, bad("Choose a valid question")
		}
		return a.trialAction(ctx, p, input.Session, input.Index, input.Answer, false)
	case "/api/rpc/finish_time_trial":
		var input struct {
			Session string `json:"p_session"`
		}
		if e := decode(w, r, &input); e != nil {
			return nil, e
		}
		return a.trialAction(ctx, p, input.Session, -1, nil, true)
	case "/api/rpc/targeted_practice":
		var input struct {
			Subject string `json:"p_subject"`
			Topic   string `json:"p_topic"`
		}
		if e := decode(w, r, &input); e != nil {
			return nil, e
		}
		return a.targetedPractice(ctx, p, input.Subject, input.Topic)
	case "/api/rpc/mistake_note":
		var input struct {
			Attempt int64  `json:"p_attempt"`
			Index   int    `json:"p_index"`
			Reason  string `json:"p_reason"`
			Note    string `json:"p_note"`
		}
		if e := decode(w, r, &input); e != nil {
			return nil, e
		}
		return a.mistakeNote(ctx, p, input.Attempt, input.Index, input.Reason, input.Note)
	case "/api/rpc/save_answers":
		var input struct {
			Session string `json:"p_session"`
			Answers []*int `json:"p_answers"`
		}
		if e := decode(w, r, &input); e != nil {
			return nil, e
		}
		return a.saveAnswers(ctx, p, input.Session, input.Answers)

	case "/api/rpc/not_studied":
		var input struct {
			Session string `json:"p_session"`
			Index   int    `json:"p_index"`
		}
		if e := decode(w, r, &input); e != nil {
			return nil, e
		}
		return a.replaceQuestion(ctx, p, input.Session, input.Index)
	case "/api/rpc/curriculum":
		var input struct {
			Grade int `json:"p_grade"`
		}
		if e := decode(w, r, &input); e != nil {
			return nil, e
		}
		if p.Profile == nil {
			return nil, forbidden()
		}
		allowed := p.Profile.Role == "student" && *p.Profile.Grade == input.Grade
		if p.Profile.Role == "parent" {
			if e := a.db.QueryRowContext(ctx, "SELECT EXISTS(SELECT 1 FROM parent_children l JOIN profiles p ON p.id=l.child_id WHERE l.parent_id=$1 AND p.grade=$2)", p.ID, input.Grade).Scan(&allowed); e != nil {
				return nil, e
			}
		}
		if !allowed {
			return nil, forbidden()
		}
		result := []map[string]any{}
		for _, sub := range a.bank[fmt.Sprint(input.Grade)] {
			raw, _ := json.Marshal(sub.Questions)
			qs, e := parseQuestions(raw)
			if e != nil {
				return nil, e
			}
			topics := map[string]int{}
			for _, q := range qs {
				topics[q.Topic]++
			}
			result = append(result, map[string]any{"subject": sub.ID, "name": sub.Name, "questions": len(qs), "topics": topics, "sources": sub.Sources})
		}
		return result, nil
	case "/api/rpc/create_link_code":
		if e := student(p); e != nil {
			return nil, e
		}
		code := strings.ToUpper(randomID())
		_, e := a.db.ExecContext(ctx, "INSERT INTO link_codes(code_hash,child_id,expires_at) VALUES($1,$2,now()+interval '15 minutes') ON CONFLICT(child_id) DO UPDATE SET code_hash=excluded.code_hash,expires_at=excluded.expires_at", hash(code), p.ID)
		return code, e
	case "/api/rpc/link_child":
		if p.Profile == nil || p.Profile.Role != "parent" {
			return nil, forbidden()
		}
		var input struct {
			Code string `json:"p_code"`
		}
		if e := decode(w, r, &input); e != nil {
			return nil, e
		}
		tx, e := a.db.BeginTx(ctx, nil)
		if e != nil {
			return nil, e
		}
		defer tx.Rollback()
		var child string
		e = tx.QueryRowContext(ctx, "DELETE FROM link_codes WHERE code_hash=$1 AND expires_at>now() RETURNING child_id", hash(strings.ToUpper(strings.TrimSpace(input.Code)))).Scan(&child)
		if errors.Is(e, sql.ErrNoRows) {
			return nil, bad("Linking code is invalid or expired")
		}
		if e != nil {
			return nil, e
		}
		if _, e = tx.ExecContext(ctx, "INSERT INTO parent_children(parent_id,child_id) VALUES($1,$2) ON CONFLICT DO NOTHING", p.ID, child); e != nil {
			return nil, e
		}
		return map[string]any{}, tx.Commit()
	case "/api/rpc/unlink_parent":
		if e := student(p); e != nil {
			return nil, e
		}
		var input struct {
			Parent string `json:"p_parent"`
		}
		if e := decode(w, r, &input); e != nil {
			return nil, e
		}
		_, e := a.db.ExecContext(ctx, "DELETE FROM parent_children WHERE child_id=$1 AND parent_id=$2", p.ID, input.Parent)
		return map[string]any{}, e
	case "/api/rpc/leaderboard":
		var input struct {
			Grade int    `json:"p_grade"`
			Week  string `json:"p_week"`
		}
		if e := decode(w, r, &input); e != nil {
			return nil, e
		}
		return a.leaderboard(ctx, p, input.Grade, input.Week)
	default:
		return nil, apiError{404, "Page not found"}
	}
}
func (a *app) availableExams(ctx context.Context, p actor) ([]exam, error) {
	if e := student(p); e != nil {
		return nil, e
	}
	tx, e := a.db.BeginTx(ctx, nil)
	if e != nil {
		return nil, e
	}
	defer tx.Rollback()
	grade := *p.Profile.Grade
	for _, s := range a.bank[fmt.Sprint(grade)] {
		questions, e := json.Marshal(s.Questions)
		if e != nil {
			return nil, e
		}
		_, e = tx.ExecContext(ctx, "INSERT INTO exams(grade,subject,title,topic,week_start,questions) VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT(grade,subject,week_start) DO UPDATE SET title=excluded.title,topic=excluded.topic,questions=excluded.questions", grade, s.ID, s.Name, s.Topic, weekStart(time.Now()), string(questions))
		if e != nil {
			return nil, e
		}
	}
	rows, e := tx.QueryContext(ctx, "SELECT id,grade,subject,title,topic,week_start::text FROM exams WHERE grade=$1 ORDER BY week_start DESC,subject", grade)
	if e != nil {
		return nil, e
	}
	result := []exam{}
	for rows.Next() {
		var v exam
		if e = rows.Scan(&v.ID, &v.Grade, &v.Subject, &v.Title, &v.Topic, &v.Week); e != nil {
			rows.Close()
			return nil, e
		}
		v.Category, v.DurationSeconds = examSettings(v.Subject)
		v.QuestionCount = 10
		result = append(result, v)
	}
	e = rows.Err()
	rows.Close()
	if e != nil {
		return nil, e
	}
	return result, tx.Commit()
}
func parseQuestions(raw []byte) ([]question, error) {
	var items []json.RawMessage
	if e := json.Unmarshal(raw, &items); e != nil {
		return nil, e
	}
	result := []question{}
	for _, item := range items {
		var fields []json.RawMessage
		if e := json.Unmarshal(item, &fields); e != nil {
			return nil, e
		}
		if len(fields) < 3 || len(fields) > 5 {
			return nil, errors.New("invalid curriculum question")
		}
		var q question
		if e := json.Unmarshal(fields[0], &q.Prompt); e != nil {
			return nil, e
		}
		if e := json.Unmarshal(fields[1], &q.Options); e != nil {
			return nil, e
		}
		if e := json.Unmarshal(fields[2], &q.Answer); e != nil {
			return nil, e
		}
		if len(fields) >= 4 {
			if e := json.Unmarshal(fields[3], &q.Topic); e != nil {
				return nil, e
			}
		}
		if len(fields) == 5 {
			var metadata struct {
				Difficulty  string `json:"difficulty"`
				Explanation string `json:"explanation"`
			}
			if e := json.Unmarshal(fields[4], &metadata); e != nil {
				return nil, e
			}
			q.Difficulty = metadata.Difficulty
			q.Explanation = metadata.Explanation
		}
		if q.Answer < 0 || q.Answer >= len(q.Options) {
			return nil, errors.New("invalid curriculum answer")
		}
		result = append(result, q)
	}
	return result, nil
}
func (a *app) startExam(ctx context.Context, p actor, id int64, mode string) (any, error) {
	if e := student(p); e != nil {
		return nil, e
	}
	if mode != "weekly" && mode != "practice" && mode != "ranked" {
		return nil, bad("Invalid exam mode")
	}
	var e exam
	var raw []byte
	err := a.db.QueryRowContext(ctx, "SELECT id,title,topic,week_start::text,questions,subject FROM exams WHERE id=$1 AND grade=$2", id, *p.Profile.Grade).Scan(&e.ID, &e.Title, &e.Topic, &e.Week, &raw, &e.Subject)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, forbidden()
	}
	if err != nil {
		return nil, err
	}
	if mode == "weekly" && e.Week != weekStart(time.Now()) {
		return nil, bad("Previous exams are available for practice only")
	}
	if mode == "weekly" {
		var done bool
		if err = a.db.QueryRowContext(ctx, "SELECT EXISTS(SELECT 1 FROM attempts WHERE student_id=$1 AND exam_id=$2 AND mode='weekly')", p.ID, id).Scan(&done); err != nil {
			return nil, err
		}
		if done {
			return nil, bad("Weekly exam already submitted. You can practise instead")
		}
	}
	if existing, err := a.resumeExam(ctx, p.ID, id, mode); err != nil {
		return nil, err
	} else if existing != nil {
		return existing, nil
	}

	questions, err := parseQuestions(raw)
	if err != nil {
		return nil, err
	}
	seed := mode + e.Week
	if mode == "ranked" {
		seed = randomID()
	}
	picked := pickQuestions(questions, 10, seed)
	if mode == "ranked" {
		picked, err = a.rankedQuestions(ctx, p.ID, e.Subject, questions)
		if err != nil {
			return nil, err
		}
	}
	snapshot, e2 := encodeQuestions(picked)
	if e2 != nil {
		return nil, e2
	}
	session := randomID()
	_, seconds := examSettings(e.Subject)
	deadline := time.Now().Add(time.Duration(seconds) * time.Second)
	_, err = a.db.ExecContext(ctx, "INSERT INTO exam_sessions(id,student_id,exam_id,mode,questions,deadline_at) VALUES($1,$2,$3,$4,$5,$6)", session, p.ID, id, mode, string(snapshot), deadline)
	return map[string]any{"session_id": session, "title": e.Title, "topic": e.Topic, "questions": picked, "answers": make([]*int, len(picked)), "deadline_at": deadline, "server_now": time.Now()}, err
}
func gradeAnswers(questions []question, answers []*int, topic string) (int, []review, error) {
	if len(questions) != len(answers) {
		return 0, nil, bad("Answer every question")
	}
	correct := 0
	reviews := []review{}
	for i, q := range questions {
		if answers[i] == nil || *answers[i] < 0 || *answers[i] >= len(q.Options) {
			return 0, nil, bad("Answer every question")
		}
		chosen := *answers[i]
		ok := chosen == q.Answer
		if ok {
			correct++
		}
		qTopic := q.Topic
		if qTopic == "" {
			qTopic = topic
		}
		reviews = append(reviews, review{q.Prompt, qTopic, q.Options[chosen], q.Options[q.Answer], ok, q.Explanation})
	}
	return correct, reviews, nil
}
func (a *app) submitExam(ctx context.Context, p actor, session string, answers []*int) (attempt, error) {
	if e := student(p); e != nil {
		return attempt{}, e
	}
	tx, e := a.db.BeginTx(ctx, nil)
	if e != nil {
		return attempt{}, e
	}
	defer tx.Rollback()
	var locked string
	if e = tx.QueryRowContext(ctx, "SELECT id FROM profiles WHERE id=$1 FOR UPDATE", p.ID).Scan(&locked); e != nil {
		return attempt{}, e
	}
	var examID int64
	var mode string
	var started time.Time
	var submitted bool
	var snapshot, unseen, saved []byte
	var deadline sql.NullTime
	e = tx.QueryRowContext(ctx, "SELECT exam_id,mode,started_at,submitted,questions,not_studied,deadline_at,saved_answers FROM exam_sessions WHERE id=$1 AND student_id=$2 FOR UPDATE", session, p.ID).Scan(&examID, &mode, &started, &submitted, &snapshot, &unseen, &deadline, &saved)
	if errors.Is(e, sql.ErrNoRows) {
		return attempt{}, forbidden()
	}
	if e != nil {
		return attempt{}, e
	}
	if mode == "time_trial" {
		return attempt{}, bad("Use the time-trial round controls to finish this round")
	}
	if submitted {
		result, e := scanAttempt(tx.QueryRowContext(ctx, "SELECT "+attemptColumns+" FROM attempts WHERE session_id=$1", session))
		return result, e
	}
	if time.Since(started) > 2*time.Hour {
		return attempt{}, bad("Exam expired. Please start again")
	}
	var ex exam
	var raw []byte
	e = tx.QueryRowContext(ctx, "SELECT grade,subject,week_start::text,topic,questions FROM exams WHERE id=$1", examID).Scan(&ex.Grade, &ex.Subject, &ex.Week, &ex.Topic, &raw)
	if e != nil {
		return attempt{}, e
	}
	if mode == "weekly" {
		if ex.Week != weekStart(time.Now()) {
			return attempt{}, bad("This weekly exam has closed")
		}
		var done bool
		if e = tx.QueryRowContext(ctx, "SELECT EXISTS(SELECT 1 FROM attempts WHERE student_id=$1 AND exam_id=$2 AND mode='weekly')", p.ID, examID).Scan(&done); e != nil {
			return attempt{}, e
		}
		if done {
			return attempt{}, bad("Weekly exam already submitted")
		}
	}
	questions, e := parseQuestions(snapshot)
	if e != nil {
		return attempt{}, e
	}
	if deadline.Valid && !time.Now().Before(deadline.Time) {
		if e = json.Unmarshal(saved, &answers); e != nil {
			return attempt{}, e
		}
		if len(answers) != len(questions) {
			answers = make([]*int, len(questions))
		}
	}
	correct, reviews, e := gradeTimedAnswers(questions, answers, ex.Topic, deadline.Valid)
	if e != nil {
		return attempt{}, e
	}
	reviewJSON, e := json.Marshal(reviews)
	if e != nil {
		return attempt{}, e
	}
	result, e := scanAttempt(tx.QueryRowContext(ctx, "INSERT INTO attempts(session_id,student_id,exam_id,grade,subject,week_start,mode,correct,total,seconds,review,not_studied) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12) RETURNING "+attemptColumns, session, p.ID, examID, ex.Grade, ex.Subject, ex.Week, mode, correct, len(questions), int(time.Since(started).Seconds()), string(reviewJSON), string(unseen)))
	if e != nil {
		return attempt{}, e
	}
	if _, e = tx.ExecContext(ctx, "UPDATE exam_sessions SET submitted=true WHERE id=$1", session); e != nil {
		return attempt{}, e
	}
	if e = recordLearning(ctx, tx, result); e != nil {
		return attempt{}, e
	}
	xp, e := awardQuizXP(ctx, tx, result)
	if e != nil {
		return attempt{}, e
	}
	rr, e := awardRankRR(ctx, tx, result)
	if e != nil {
		return attempt{}, e
	}
	result.RRDelta = rr
	result.XPEarned = xp
	if _, e = tx.ExecContext(ctx, "UPDATE attempts SET xp_earned=$1,rr_delta=$2 WHERE id=$3", xp, rr, result.ID); e != nil {
		return attempt{}, e
	}
	return result, tx.Commit()
}
func (a *app) leaderboard(ctx context.Context, p actor, grade int, week string) (any, error) {
	if t, e := time.Parse("2006-01-02", week); e != nil || t.Weekday() != time.Monday {
		return nil, bad("Choose a valid week")
	}
	if p.Profile == nil {
		return nil, forbidden()
	}
	allowed := p.Profile.Role == "student" && *p.Profile.Grade == grade
	if p.Profile.Role == "parent" {
		if e := a.db.QueryRowContext(ctx, "SELECT EXISTS(SELECT 1 FROM parent_children l JOIN profiles p ON p.id=l.child_id WHERE l.parent_id=$1 AND p.grade=$2)", p.ID, grade).Scan(&allowed); e != nil {
			return nil, e
		}
	}
	if !allowed {
		return nil, forbidden()
	}
	rows, e := a.db.QueryContext(ctx, `WITH best AS (SELECT student_id,exam_id,max(correct::numeric/GREATEST(total,1)) pct FROM attempts WHERE grade=$1 AND week_start=$2 AND mode IN ('weekly','ranked') GROUP BY student_id,exam_id), scores AS (
 SELECT student_id,round(sum(pct) / GREATEST(1,(SELECT count(*) FROM exams WHERE grade=$1 AND week_start=$2))*100,1) score,count(*) completed
 FROM best GROUP BY student_id
 ) SELECT rank() OVER(ORDER BY score DESC), 'Learner '||substr(student_id,1,8),score::float8,completed,
 (student_id=$3 OR EXISTS(SELECT 1 FROM parent_children WHERE parent_id=$3 AND child_id=student_id)),
 (SELECT count(*) FROM exams WHERE grade=$1 AND week_start=$2)
 FROM scores ORDER BY score DESC,student_id`, grade, week, p.ID)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	result := []map[string]any{}
	for rows.Next() {
		var rank, completed, examCount int64
		var label string
		var score float64
		var own bool
		if e = rows.Scan(&rank, &label, &score, &completed, &own, &examCount); e != nil {
			return nil, e
		}
		result = append(result, map[string]any{"position": rank, "label": label, "score": score, "completed": completed, "is_you": own, "exam_count": examCount})
	}
	return result, rows.Err()
}

type rateEntry struct {
	Count int
	Start time.Time
}
type rateLimiter struct {
	sync.Mutex
	entries map[string]rateEntry
}

func newRateLimiter() *rateLimiter { return &rateLimiter{entries: map[string]rateEntry{}} }
func (l *rateLimiter) allow(key string, now time.Time) bool {
	l.Lock()
	defer l.Unlock()
	for k, v := range l.entries {
		if now.Sub(v.Start) > 10*time.Minute {
			delete(l.entries, k)
		}
	}
	e := l.entries[key]
	if e.Start.IsZero() {
		e.Start = now
	}
	e.Count++
	l.entries[key] = e
	return e.Count <= 30
}
