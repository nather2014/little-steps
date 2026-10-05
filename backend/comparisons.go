package main

import (
	"context"
	"database/sql"
	"time"
)

func (a *app) comparisons(ctx context.Context, p actor, id string) (any, error) {
	if id == "" {
		id = p.ID
	}
	if e := a.canRead(ctx, p, id); e != nil {
		return nil, e
	}
	query := "WITH own AS (SELECT a.*,e.title,COALESCE(t.duration_seconds,0) duration_seconds FROM attempts a JOIN exams e ON e.id=a.exam_id LEFT JOIN time_trials t ON t.attempt_id=a.id WHERE a.student_id=$1)," +
		"own_exams AS (SELECT DISTINCT exam_id,mode,duration_seconds FROM own)," +
		"first_scores AS (SELECT DISTINCT ON (a.exam_id,a.mode,COALESCE(t.duration_seconds,0),a.student_id) a.exam_id,a.mode,COALESCE(t.duration_seconds,0) duration_seconds,a.student_id,100.0*a.correct/NULLIF(a.total,0) pct " +
		"FROM attempts a LEFT JOIN time_trials t ON t.attempt_id=a.id JOIN own_exams e ON e.exam_id=a.exam_id AND e.mode=a.mode AND e.duration_seconds=COALESCE(t.duration_seconds,0) WHERE a.student_id<>$1 " +
		"ORDER BY a.exam_id,a.mode,COALESCE(t.duration_seconds,0),a.student_id,a.submitted_at,a.id)," +
		"averages AS (SELECT exam_id,mode,duration_seconds,count(*) learners,round(avg(pct),1) average FROM first_scores GROUP BY exam_id,mode,duration_seconds) " +
		"SELECT o.id,o.exam_id,o.subject,o.title,o.week_start::text,o.mode,o.submitted_at,round(100.0*o.correct/NULLIF(o.total,0),1)," +
		"COALESCE(v.learners,0),CASE WHEN v.learners>=3 THEN v.average ELSE NULL END,o.duration_seconds " +
		"FROM own o LEFT JOIN averages v ON v.exam_id=o.exam_id AND v.mode=o.mode AND v.duration_seconds=o.duration_seconds ORDER BY o.submitted_at DESC,o.id DESC LIMIT 100"
	rows, e := a.db.QueryContext(ctx, query, id)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	result := []map[string]any{}
	for rows.Next() {
		var attemptID, examID, learners int64
		var subject, title, week, mode string
		var date time.Time
		var score float64
		var average sql.NullFloat64
		var duration int
		if e = rows.Scan(&attemptID, &examID, &subject, &title, &week, &mode, &date, &score, &learners, &average, &duration); e != nil {
			return nil, e
		}
		var avg any
		if average.Valid {
			avg = average.Float64
		}
		result = append(result, map[string]any{"attempt_id": attemptID, "exam_id": examID, "subject": subject, "title": title, "week_start": week, "mode": mode, "submitted_at": date, "score": score, "peer_count": learners, "average": avg, "duration_seconds": duration})
	}
	return result, rows.Err()
}
