package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"
)

var learningZone = func() *time.Location {
	z, e := time.LoadLocation("Asia/Kolkata")
	if e != nil {
		panic(e)
	}
	return z
}()

func learningPeriods(now time.Time) (time.Time, time.Time, time.Time, time.Time) {
	local := now.In(learningZone)
	day := time.Date(local.Year(), local.Month(), local.Day(), 0, 0, 0, 0, learningZone)
	week := day.AddDate(0, 0, -(int(day.Weekday())+6)%7)
	return day, day.AddDate(0, 0, 1), week, week.AddDate(0, 0, 7)
}

type rewardReader interface {
	QueryRowContext(context.Context, string, ...any) *sql.Row
	QueryContext(context.Context, string, ...any) (*sql.Rows, error)
}

func awardQuizXP(ctx context.Context, tx *sql.Tx, a attempt) (int, error) {
	day, end, _, _ := learningPeriods(a.Date)
	if a.Mode == "practice" {
		var prior int
		if e := tx.QueryRowContext(ctx, "SELECT count(*) FROM xp_events x JOIN attempts a ON a.id=x.attempt_id WHERE x.student_id=$1 AND x.kind='quiz' AND a.mode='practice' AND x.earned_at >= $2 AND x.earned_at < $3", a.Student, day, end).Scan(&prior); e != nil {
			return 0, e
		}
		if prior >= 3 {
			return 0, nil
		}
	}
	base := 40
	title := "Practice quiz"
	if a.Mode != "practice" {
		base = 100
		title = "Ranked test"
	}
	base += a.Correct * 10
	if a.Mode == "time_trial" {
		var prior int
		if e := tx.QueryRowContext(ctx, "SELECT count(*) FROM xp_events x JOIN attempts a ON a.id=x.attempt_id WHERE x.student_id=$1 AND x.kind='quiz' AND a.mode='time_trial' AND x.earned_at>=$2 AND x.earned_at<$3", a.Student, day, end).Scan(&prior); e != nil {
			return 0, e
		}
		if prior >= 3 || a.Correct == 0 {
			return 0, nil
		}
		base = 5 * a.Correct
		title = "Time trial"
	}

	var earned int
	e := tx.QueryRowContext(ctx, "INSERT INTO xp_events(student_id,event_key,kind,title,amount,attempt_id,earned_at) VALUES($1,$2,'quiz',$3,$4,$5,$6) ON CONFLICT(student_id,event_key) DO NOTHING RETURNING amount", a.Student, fmt.Sprintf("attempt:%d", a.ID), title, base, a.ID, a.Date).Scan(&earned)
	if errors.Is(e, sql.ErrNoRows) {
		return 0, nil
	}
	if e != nil {
		return 0, e
	}
	return earned, nil
}
func levelInfo(xp int) (int, int, string) {
	level := 1 + xp/500
	name := "Sprout"
	if level >= 5 {
		name = "Explorer"
	}
	if level >= 10 {
		name = "Builder"
	}
	if level >= 20 {
		name = "Trailblazer"
	}
	return level, xp % 500, name
}
func (a *app) rewards(ctx context.Context, p actor, id string, now time.Time) (any, error) {
	if id == "" {
		id = p.ID
	}
	if e := a.canRead(ctx, p, id); e != nil {
		return nil, e
	}
	tx, e := a.db.BeginTx(ctx, &sql.TxOptions{ReadOnly: true, Isolation: sql.LevelRepeatableRead})
	if e != nil {
		return nil, e
	}
	defer tx.Rollback()
	var total, quizzes, subjects, correct int
	e = tx.QueryRowContext(ctx, "SELECT COALESCE(sum(amount),0) FROM xp_events WHERE student_id=$1", id).Scan(&total)
	if e != nil {
		return nil, e
	}
	day, end, week, weekEnd := learningPeriods(now)
	var practiceToday int
	e = tx.QueryRowContext(ctx, "SELECT count(*) FROM xp_events x JOIN attempts a ON a.id=x.attempt_id WHERE x.student_id=$1 AND x.kind='quiz' AND a.mode='practice' AND x.earned_at >= $2 AND x.earned_at < $3", id, day, end).Scan(&practiceToday)
	if e != nil {
		return nil, e
	}
	e = tx.QueryRowContext(ctx, "SELECT count(*),count(DISTINCT a.subject),COALESCE(sum(a.correct),0) FROM xp_events x JOIN attempts a ON a.id=x.attempt_id WHERE x.student_id=$1 AND x.kind='quiz'", id).Scan(&quizzes, &subjects, &correct)
	if e != nil {
		return nil, e
	}
	badges := []map[string]any{
		{"id": "first_step", "name": "First Step", "description": "Complete your first learning quiz", "earned": quizzes >= 1},
		{"id": "curious_mind", "name": "Curious Mind", "description": "Learn across three subjects", "earned": subjects >= 3},
		{"id": "steady_learner", "name": "Steady Learner", "description": "Complete ten rewarded quizzes", "earned": quizzes >= 10},
		{"id": "problem_solver", "name": "Problem Solver", "description": "Find fifty correct answers", "earned": correct >= 50},
	}
	rows, e := tx.QueryContext(ctx, "SELECT title,amount,earned_at FROM xp_events WHERE student_id=$1 ORDER BY earned_at DESC,id DESC LIMIT 10", id)
	if e != nil {
		return nil, e
	}
	recent := []map[string]any{}
	for rows.Next() {
		var title string
		var xp int
		var date time.Time
		if e = rows.Scan(&title, &xp, &date); e != nil {
			rows.Close()
			return nil, e
		}
		recent = append(recent, map[string]any{"title": title, "xp": xp, "earned_at": date})
	}
	e = rows.Err()
	rows.Close()
	if e != nil {
		return nil, e
	}
	rank, e := readRank(ctx, tx, id)
	if e != nil {
		return nil, e
	}
	level, into, name := levelInfo(total)
	if e = tx.Commit(); e != nil {
		return nil, e
	}
	remaining := 3 - practiceToday
	if remaining < 0 {
		remaining = 0
	}
	return map[string]any{"rank": rank, "xp": total, "level": level, "level_name": name, "level_xp": into, "level_target": 500, "daily": []struct{}{}, "weekly": []struct{}{}, "badges": badges, "recent": recent, "practice_rewards_left": remaining, "daily_date": day.Format("2006-01-02"), "week_start": week.Format("2006-01-02"), "daily_reset": end, "weekly_reset": weekEnd, "timezone": "Asia/Kolkata"}, nil
}
