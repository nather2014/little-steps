package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"strings"
	"time"
)

func examSettings(subject string) (string, int) {
	if strings.HasPrefix(subject, "olympiad_") {
		return "olympiad", 1200
	}
	return "regular", 900
}

func (a *app) resumeExam(ctx context.Context, studentID string, examID int64, mode string) (any, error) {
	var session, title, topic string
	var raw, saved []byte
	var deadline sql.NullTime
	err := a.db.QueryRowContext(ctx, "SELECT s.id,e.title,e.topic,s.questions,s.saved_answers,s.deadline_at FROM exam_sessions s JOIN exams e ON e.id=s.exam_id WHERE s.student_id=$1 AND s.exam_id=$2 AND s.mode=$3 AND NOT s.submitted AND s.started_at>now()-interval '2 hours' ORDER BY s.started_at DESC LIMIT 1", studentID, examID, mode).Scan(&session, &title, &topic, &raw, &saved, &deadline)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	qs, err := parseQuestions(raw)
	if err != nil {
		return nil, err
	}
	var answers []*int
	if err = json.Unmarshal(saved, &answers); err != nil {
		return nil, err
	}
	if len(answers) != len(qs) {
		answers = make([]*int, len(qs))
	}
	var expires any
	if deadline.Valid {
		expires = deadline.Time
	}
	return map[string]any{"session_id": session, "title": title, "topic": topic, "questions": qs, "answers": answers, "deadline_at": expires, "server_now": time.Now()}, nil
}

func (a *app) saveAnswers(ctx context.Context, p actor, session string, answers []*int) (any, error) {
	if err := student(p); err != nil {
		return nil, err
	}
	tx, err := a.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()
	var raw []byte
	var deadline sql.NullTime
	var submitted bool
	var mode string
	err = tx.QueryRowContext(ctx, "SELECT questions,deadline_at,submitted,mode FROM exam_sessions WHERE id=$1 AND student_id=$2 FOR UPDATE", session, p.ID).Scan(&raw, &deadline, &submitted, &mode)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, forbidden()
	}
	if err != nil {
		return nil, err
	}
	if mode == "time_trial" {
		return nil, bad("Answer one time-trial question at a time")
	}
	if submitted {
		return nil, bad("This exam has already been submitted")
	}
	if deadline.Valid && !time.Now().Before(deadline.Time) {
		return nil, bad("Time is up. Submit your saved answers.")
	}
	qs, err := parseQuestions(raw)
	if err != nil {
		return nil, err
	}
	if _, _, err = gradeTimedAnswers(qs, answers, "", true); err != nil {
		return nil, err
	}
	encoded, err := json.Marshal(answers)
	if err != nil {
		return nil, err
	}
	if _, err = tx.ExecContext(ctx, "UPDATE exam_sessions SET saved_answers=$1 WHERE id=$2", string(encoded), session); err != nil {
		return nil, err
	}
	return map[string]any{"saved": true}, tx.Commit()
}

func gradeTimedAnswers(qs []question, answers []*int, topic string, allowBlank bool) (int, []review, error) {
	if !allowBlank {
		return gradeAnswers(qs, answers, topic)
	}
	if len(qs) != len(answers) {
		return 0, nil, bad("Invalid answer count")
	}
	correct := 0
	reviews := []review{}
	for i, q := range qs {
		selected := "Not answered"
		ok := false
		if answers[i] != nil {
			if *answers[i] < 0 || *answers[i] >= len(q.Options) {
				return 0, nil, bad("Invalid answer")
			}
			selected = q.Options[*answers[i]]
			ok = *answers[i] == q.Answer
		}
		if ok {
			correct++
		}
		t := q.Topic
		if t == "" {
			t = topic
		}
		reviews = append(reviews, review{q.Prompt, t, selected, q.Options[q.Answer], ok, q.Explanation})
	}
	return correct, reviews, nil
}
