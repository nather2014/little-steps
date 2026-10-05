package main

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/json"
	"errors"
	"sort"
	"time"
)

type trialAnswer struct {
	Review review `json:"review"`
	Points int    `json:"points"`
}
type trial struct {
	ID, Student, Subject, Title, Week           string
	Exam                                        int64
	Grade, Duration, Points, Streak, BestStreak int
	Started, Deadline                           time.Time
	Finished                                    sql.NullTime
	Attempt                                     sql.NullInt64
	Pool                                        []question
	Answers                                     []trialAnswer
}

func trialPoints(correct bool, streak int) (int, int) {
	if !correct {
		return 0, 0
	}
	streak++
	bonus := streak - 1
	if bonus > 5 {
		bonus = 5
	}
	return 10 + 2*bonus, streak
}
func shuffledTrialQuestions(qs []question) []question {
	result := append([]question(nil), qs...)
	seed := randomID()
	sort.Slice(result, func(i, j int) bool {
		x := sha256.Sum256([]byte(seed + result[i].Prompt))
		y := sha256.Sum256([]byte(seed + result[j].Prompt))
		return string(x[:]) < string(y[:])
	})
	return result
}
func (a *app) startTrial(ctx context.Context, p actor, examID int64, seconds int) (any, error) {
	if e := student(p); e != nil {
		return nil, e
	}
	if seconds != 60 && seconds != 180 && seconds != 300 {
		return nil, bad("Choose a 60-second, 3-minute or 5-minute round")
	}
	tx, e := a.db.BeginTx(ctx, nil)
	if e != nil {
		return nil, e
	}
	defer tx.Rollback()
	var locked string
	if e = tx.QueryRowContext(ctx, "SELECT id FROM profiles WHERE id=$1 FOR UPDATE", p.ID).Scan(&locked); e != nil {
		return nil, e
	}
	var title string
	var raw []byte
	e = tx.QueryRowContext(ctx, "SELECT title,questions FROM exams WHERE id=$1 AND grade=$2", examID, *p.Profile.Grade).Scan(&title, &raw)
	if errors.Is(e, sql.ErrNoRows) {
		return nil, forbidden()
	}
	if e != nil {
		return nil, e
	}
	var existing string
	e = tx.QueryRowContext(ctx, "SELECT s.id FROM exam_sessions s JOIN time_trials t ON t.session_id=s.id WHERE s.student_id=$1 AND s.exam_id=$2 AND t.duration_seconds=$3 AND t.finished_at IS NULL ORDER BY s.started_at DESC LIMIT 1", p.ID, examID, seconds).Scan(&existing)
	if e != nil && !errors.Is(e, sql.ErrNoRows) {
		return nil, e
	}
	if existing != "" {
		if e = tx.Commit(); e != nil {
			return nil, e
		}
		return a.trialAction(ctx, p, existing, -1, nil, false)
	}
	qs, e := parseQuestions(raw)
	if e != nil {
		return nil, e
	}
	if len(qs) == 0 {
		return nil, bad("This subject has no questions yet")
	}
	snapshot, e := encodeQuestions(shuffledTrialQuestions(qs))
	if e != nil {
		return nil, e
	}
	id := randomID()
	now := time.Now()
	deadline := now.Add(time.Duration(seconds) * time.Second)
	_, e = tx.ExecContext(ctx, "INSERT INTO exam_sessions(id,student_id,exam_id,mode,questions,started_at,deadline_at) VALUES($1,$2,$3,'time_trial',$4,$5,$6)", id, p.ID, examID, string(snapshot), now, deadline)
	if e != nil {
		return nil, e
	}
	_, e = tx.ExecContext(ctx, "INSERT INTO time_trials(session_id,duration_seconds) VALUES($1,$2)", id, seconds)
	if e != nil {
		return nil, e
	}
	if e = tx.Commit(); e != nil {
		return nil, e
	}
	return a.trialAction(ctx, p, id, -1, nil, false)
}
func loadTrial(ctx context.Context, tx *sql.Tx, id, studentID string) (trial, error) {
	var t trial
	var pool, answers []byte
	e := tx.QueryRowContext(ctx, "SELECT s.id,s.student_id,s.exam_id,e.grade,e.subject,e.title,e.week_start::text,s.started_at,s.deadline_at,s.questions,t.duration_seconds,t.answers,t.points,t.streak,t.best_streak,t.finished_at,t.attempt_id FROM exam_sessions s JOIN time_trials t ON t.session_id=s.id JOIN exams e ON e.id=s.exam_id WHERE s.id=$1 AND s.student_id=$2 FOR UPDATE OF s,t", id, studentID).Scan(&t.ID, &t.Student, &t.Exam, &t.Grade, &t.Subject, &t.Title, &t.Week, &t.Started, &t.Deadline, &pool, &t.Duration, &answers, &t.Points, &t.Streak, &t.BestStreak, &t.Finished, &t.Attempt)
	if errors.Is(e, sql.ErrNoRows) {
		return t, forbidden()
	}
	if e != nil {
		return t, e
	}
	t.Pool, e = parseQuestions(pool)
	if e != nil {
		return t, e
	}
	if len(t.Pool) == 0 {
		return t, bad("This round has no questions")
	}
	e = json.Unmarshal(answers, &t.Answers)
	return t, e
}
func trialState(t trial) map[string]any {
	return map[string]any{"session_id": t.ID, "title": t.Title, "subject": t.Subject, "duration_seconds": t.Duration, "started_at": t.Started, "deadline_at": t.Deadline, "server_now": time.Now(), "index": len(t.Answers), "question": t.Pool[len(t.Answers)%len(t.Pool)], "points": t.Points, "streak": t.Streak, "best_streak": t.BestStreak, "answered": len(t.Answers), "finished": false}
}
func trialFeedback(answer trialAnswer) map[string]any {
	return map[string]any{"correct": answer.Review.Correct, "selected": answer.Review.Selected, "answer": answer.Review.Answer, "explanation": answer.Review.Explanation, "points": answer.Points}
}
func (a *app) trialAction(ctx context.Context, p actor, id string, index int, choice *int, finish bool) (any, error) {
	if e := student(p); e != nil {
		return nil, e
	}
	tx, e := a.db.BeginTx(ctx, nil)
	if e != nil {
		return nil, e
	}
	defer tx.Rollback()
	var locked string
	if e = tx.QueryRowContext(ctx, "SELECT id FROM profiles WHERE id=$1 FOR UPDATE", p.ID).Scan(&locked); e != nil {
		return nil, e
	}
	t, e := loadTrial(ctx, tx, id, p.ID)
	if e != nil {
		return nil, e
	}
	now := time.Now()
	if t.Finished.Valid || finish || !now.Before(t.Deadline) {
		result, e := a.finishTrial(ctx, tx, &t, now)
		if e != nil {
			return nil, e
		}
		if e = tx.Commit(); e != nil {
			return nil, e
		}
		return map[string]any{"finished": true, "result": result}, nil
	}
	var feedback any
	if index >= 0 {
		if index > len(t.Answers) {
			return nil, bad("Answer the current question first")
		}
		if index < len(t.Answers) {
			feedback = trialFeedback(t.Answers[index])
		} else {
			q := t.Pool[index%len(t.Pool)]
			selected := "Skipped"
			correct := false
			if choice != nil {
				if *choice < 0 || *choice >= len(q.Options) {
					return nil, bad("Choose a valid answer")
				}
				selected = q.Options[*choice]
				correct = *choice == q.Answer
			}
			points, streak := trialPoints(correct, t.Streak)
			t.Points += points
			t.Streak = streak
			if streak > t.BestStreak {
				t.BestStreak = streak
			}
			answer := trialAnswer{Review: review{q.Prompt, q.Topic, selected, q.Options[q.Answer], correct, q.Explanation}, Points: points}
			t.Answers = append(t.Answers, answer)
			encoded, e := json.Marshal(t.Answers)
			if e != nil {
				return nil, e
			}
			_, e = tx.ExecContext(ctx, "UPDATE time_trials SET answers=$2,points=$3,streak=$4,best_streak=$5 WHERE session_id=$1", id, string(encoded), t.Points, t.Streak, t.BestStreak)
			if e != nil {
				return nil, e
			}
			feedback = trialFeedback(answer)
		}
	}
	result := trialState(t)
	if feedback != nil {
		result["feedback"] = feedback
	}
	if e = tx.Commit(); e != nil {
		return nil, e
	}
	return result, nil
}
func (a *app) finishTrial(ctx context.Context, tx *sql.Tx, t *trial, now time.Time) (any, error) {
	xp := 0
	correct := 0
	reviews := []review{}
	for _, answer := range t.Answers {
		reviews = append(reviews, answer.Review)
		if answer.Review.Correct {
			correct++
		}
	}
	first := !t.Finished.Valid
	if first {
		end := now
		if end.After(t.Deadline) {
			end = t.Deadline
		}
		t.Finished = sql.NullTime{Time: end, Valid: true}
		if len(reviews) > 0 {
			raw, e := json.Marshal(reviews)
			if e != nil {
				return nil, e
			}
			result, e := scanAttempt(tx.QueryRowContext(ctx, "INSERT INTO attempts(session_id,student_id,exam_id,grade,subject,week_start,mode,correct,total,seconds,submitted_at,review) VALUES($1,$2,$3,$4,$5,$6,'time_trial',$7,$8,$9,$10,$11) RETURNING "+attemptColumns, t.ID, t.Student, t.Exam, t.Grade, t.Subject, t.Week, correct, len(reviews), int(end.Sub(t.Started).Seconds()), now, string(raw)))
			if e != nil {
				return nil, e
			}
			t.Attempt = sql.NullInt64{Int64: result.ID, Valid: true}
			if e = recordLearning(ctx, tx, result); e != nil {
				return nil, e
			}
			xp, e = awardQuizXP(ctx, tx, result)
			if e != nil {
				return nil, e
			}
			if _, e = tx.ExecContext(ctx, "UPDATE attempts SET xp_earned=$2 WHERE id=$1", result.ID, xp); e != nil {
				return nil, e
			}
		}
		var attemptID any
		if t.Attempt.Valid {
			attemptID = t.Attempt.Int64
		}
		if _, e := tx.ExecContext(ctx, "UPDATE time_trials SET finished_at=$2,attempt_id=$3 WHERE session_id=$1", t.ID, t.Finished.Time, attemptID); e != nil {
			return nil, e
		}
		if _, e := tx.ExecContext(ctx, "UPDATE exam_sessions SET submitted=true WHERE id=$1", t.ID); e != nil {
			return nil, e
		}
	} else if t.Attempt.Valid {
		if e := tx.QueryRowContext(ctx, "SELECT xp_earned FROM attempts WHERE id=$1", t.Attempt.Int64).Scan(&xp); e != nil {
			return nil, e
		}
	}
	var previous int
	e := tx.QueryRowContext(ctx, "SELECT COALESCE(max(t.points),0) FROM time_trials t JOIN exam_sessions s ON s.id=t.session_id JOIN exams e ON e.id=s.exam_id WHERE s.student_id=$1 AND e.subject=$2 AND t.duration_seconds=$3 AND t.finished_at IS NOT NULL AND t.session_id<>$4", t.Student, t.Subject, t.Duration, t.ID).Scan(&previous)
	if e != nil {
		return nil, e
	}
	best := previous
	if t.Points > best {
		best = t.Points
	}
	elapsed := t.Finished.Time.Sub(t.Started).Seconds()
	if elapsed < 1 {
		elapsed = 1
	}
	accuracy := 0
	if len(reviews) > 0 {
		accuracy = 100 * correct / len(reviews)
	}
	var attemptID any
	if t.Attempt.Valid {
		attemptID = t.Attempt.Int64
	}
	return map[string]any{"session_id": t.ID, "attempt_id": attemptID, "subject": t.Subject, "title": t.Title, "duration_seconds": t.Duration, "seconds": int(elapsed), "points": t.Points, "answered": len(reviews), "correct": correct, "accuracy": accuracy, "best_streak": t.BestStreak, "correct_per_minute": float64(correct) * 60 / elapsed, "personal_best": best, "new_best": first && t.Points > previous, "xp_earned": xp, "rr_delta": 0, "review": reviews}, nil
}
func (a *app) trialHistory(ctx context.Context, p actor, id string) (any, error) {
	if id == "" {
		id = p.ID
	}
	if e := a.canRead(ctx, p, id); e != nil {
		return nil, e
	}
	rows, e := a.db.QueryContext(ctx, "SELECT t.session_id,e.subject,e.title,t.duration_seconds,t.points,t.best_streak,jsonb_array_length(t.answers),s.started_at,s.deadline_at,t.finished_at FROM time_trials t JOIN exam_sessions s ON s.id=t.session_id JOIN exams e ON e.id=s.exam_id WHERE s.student_id=$1 ORDER BY s.started_at DESC LIMIT 20", id)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	recent := []map[string]any{}
	for rows.Next() {
		var sid, subject, title string
		var duration, points, streak, answered int
		var started, deadline time.Time
		var finished sql.NullTime
		if e = rows.Scan(&sid, &subject, &title, &duration, &points, &streak, &answered, &started, &deadline, &finished); e != nil {
			return nil, e
		}
		recent = append(recent, map[string]any{"session_id": sid, "subject": subject, "title": title, "duration_seconds": duration, "points": points, "best_streak": streak, "answered": answered, "started_at": started, "deadline_at": deadline, "finished": finished.Valid})
	}
	if e = rows.Err(); e != nil {
		return nil, e
	}
	br, e := a.db.QueryContext(ctx, "SELECT e.subject,t.duration_seconds,max(t.points),max(t.best_streak),count(*) FROM time_trials t JOIN exam_sessions s ON s.id=t.session_id JOIN exams e ON e.id=s.exam_id WHERE s.student_id=$1 AND t.finished_at IS NOT NULL GROUP BY e.subject,t.duration_seconds ORDER BY e.subject,t.duration_seconds", id)
	if e != nil {
		return nil, e
	}
	defer br.Close()
	bests := []map[string]any{}
	for br.Next() {
		var subject string
		var duration, points, streak, rounds int
		if e = br.Scan(&subject, &duration, &points, &streak, &rounds); e != nil {
			return nil, e
		}
		bests = append(bests, map[string]any{"subject": subject, "duration_seconds": duration, "points": points, "best_streak": streak, "rounds": rounds})
	}
	if e = br.Err(); e != nil {
		return nil, e
	}
	return map[string]any{"recent": recent, "bests": bests}, nil
}
