package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"
)

var rankNames = []string{"Iron", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Ascendant", "Immortal", "Radiant"}

func rankInfo(points int) map[string]any {
	if points < 0 {
		points = 0
	}
	tier := points / 300
	if tier >= 8 {
		return map[string]any{"tier": "Radiant", "division": 1, "name": "Radiant", "rr": points - 2400, "points": points, "next_rank": nil, "rr_needed": 0}
	}
	division := (points%300)/100 + 1
	next := fmt.Sprintf("%s %d", rankNames[tier], division+1)
	if division == 3 {
		if tier == 7 {
			next = "Radiant"
		} else {
			next = rankNames[tier+1] + " 1"
		}
	}
	return map[string]any{"tier": rankNames[tier], "division": division, "name": fmt.Sprintf("%s %d", rankNames[tier], division), "rr": points % 100, "points": points, "next_rank": next, "rr_needed": 100 - points%100}
}
func scoreRR(correct, total int) int {
	if total <= 0 {
		return 0
	}
	pct := 100 * correct / total
	switch {
	case pct >= 90:
		return 30
	case pct >= 75:
		return 20
	case pct >= 60:
		return 10
	case pct >= 40:
		return -10
	default:
		return -20
	}
}
func awardRankRR(ctx context.Context, tx *sql.Tx, a attempt) (int, error) {
	if a.Mode != "weekly" && a.Mode != "ranked" {
		return 0, nil
	}
	before := 50
	e := tx.QueryRowContext(ctx, "SELECT after_points FROM rank_events WHERE student_id=$1 ORDER BY id DESC LIMIT 1", a.Student).Scan(&before)
	if e != nil && !errors.Is(e, sql.ErrNoRows) {
		return 0, e
	}
	after := before + scoreRR(a.Correct, a.Total)
	if after < 0 {
		after = 0
	}
	delta := after - before
	var stored int
	e = tx.QueryRowContext(ctx, "INSERT INTO rank_events(student_id,attempt_id,delta,before_points,after_points,awarded_at) VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT(attempt_id) DO NOTHING RETURNING delta", a.Student, a.ID, delta, before, after, a.Date).Scan(&stored)
	if errors.Is(e, sql.ErrNoRows) {
		return 0, nil
	}
	return stored, e
}
func readRank(ctx context.Context, q rewardReader, id string) (map[string]any, error) {
	points := 50
	e := q.QueryRowContext(ctx, "SELECT after_points FROM rank_events WHERE student_id=$1 ORDER BY id DESC LIMIT 1", id).Scan(&points)
	if e != nil && !errors.Is(e, sql.ErrNoRows) {
		return nil, e
	}
	result := rankInfo(points)
	rows, e := q.QueryContext(ctx, "SELECT r.delta,r.before_points,r.after_points,r.awarded_at,e.title,100.0*a.correct/a.total FROM rank_events r JOIN attempts a ON a.id=r.attempt_id JOIN exams e ON e.id=a.exam_id WHERE r.student_id=$1 ORDER BY r.id DESC LIMIT 8", id)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	recent := []map[string]any{}
	for rows.Next() {
		var delta, before, after int
		var when time.Time
		var title string
		var score float64
		if e = rows.Scan(&delta, &before, &after, &when, &title, &score); e != nil {
			return nil, e
		}
		recent = append(recent, map[string]any{"delta": delta, "before": before, "after": after, "date": when, "title": title, "score": score, "rank": rankInfo(after)["name"]})
	}
	result["recent"] = recent
	result["starting_points"] = 50
	result["tiers"] = rankNames
	return result, rows.Err()
}
