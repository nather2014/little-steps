package main

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"sort"
	"time"
)

func (a *app) subjectCount(grade int) int { return len(a.bank[fmt.Sprint(grade)]) }

// Pick across topics first. Weekly sets are reproducible; practice sets vary.
func pickQuestions(pool []question, count int, seed string) []question {
	if len(pool) <= count {
		return append([]question(nil), pool...)
	}
	if len(seed) >= 8 && seed[:8] == "practice" {
		seed = randomID()
	}
	shuffled := append([]question(nil), pool...)
	sort.Slice(shuffled, func(i, j int) bool {
		x := sha256.Sum256([]byte(seed + shuffled[i].Prompt))
		y := sha256.Sum256([]byte(seed + shuffled[j].Prompt))
		return string(x[:]) < string(y[:])
	})
	result := []question{}
	topics := map[string]bool{}
	used := map[string]bool{}
	for _, q := range shuffled {
		if !topics[q.Topic] {
			result = append(result, q)
			topics[q.Topic] = true
			used[q.Prompt] = true
			if len(result) == count {
				return result
			}
		}
	}
	for _, q := range shuffled {
		if !used[q.Prompt] {
			result = append(result, q)
			if len(result) == count {
				return result
			}
		}
	}
	return result
}
func encodeQuestions(qs []question) ([]byte, error) {
	rows := make([][]any, 0, len(qs))
	for _, q := range qs {
		rows = append(rows, []any{q.Prompt, q.Options, q.Answer, q.Topic, map[string]string{"difficulty": q.Difficulty, "explanation": q.Explanation}})
	}
	return json.Marshal(rows)
}
func (a *app) replaceQuestion(ctx context.Context, p actor, session string, index int) (any, error) {
	if e := student(p); e != nil {
		return nil, e
	}
	tx, e := a.db.BeginTx(ctx, nil)
	if e != nil {
		return nil, e
	}
	defer tx.Rollback()
	var raw, unseen, poolRaw []byte
	var submitted bool
	var started time.Time
	var deadline sql.NullTime
	var saved []byte
	var fallback, mode string
	e = tx.QueryRowContext(ctx, "SELECT s.questions,s.not_studied,s.submitted,s.started_at,e.questions,e.topic,s.deadline_at,s.saved_answers,s.mode FROM exam_sessions s JOIN exams e ON e.id=s.exam_id WHERE s.id=$1 AND s.student_id=$2 FOR UPDATE OF s", session, p.ID).Scan(&raw, &unseen, &submitted, &started, &poolRaw, &fallback, &deadline, &saved, &mode)
	if errors.Is(e, sql.ErrNoRows) {
		return nil, forbidden()
	}
	if e != nil {
		return nil, e
	}
	if mode == "time_trial" {
		return nil, bad("Use Skip in a time-trial round")
	}
	if submitted {
		return nil, bad("This exam has already been submitted")
	}
	if deadline.Valid && !time.Now().Before(deadline.Time) {
		return nil, bad("Time is up. Submit your saved answers.")
	}
	if time.Since(started) > 2*time.Hour {
		return nil, bad("Exam expired. Please start again")
	}
	qs, e := parseQuestions(raw)
	if e != nil {
		return nil, e
	}
	if index < 0 || index >= len(qs) {
		return nil, bad("Choose a valid question")
	}
	pool, e := parseQuestions(poolRaw)
	if e != nil {
		return nil, e
	}
	var marked []unseenTopic
	if e = json.Unmarshal(unseen, &marked); e != nil {
		return nil, e
	}
	blocked := map[string]bool{}
	used := map[string]bool{}
	for _, q := range qs {
		used[q.Prompt] = true
	}
	for _, q := range marked {
		blocked[q.Topic] = true
		used[q.Prompt] = true
	}
	current := qs[index]
	topic := current.Topic
	if topic == "" {
		topic = fallback
	}
	blocked[topic] = true
	candidates := []question{}
	for _, q := range pool {
		if !used[q.Prompt] && !blocked[q.Topic] {
			candidates = append(candidates, q)
		}
	}
	if len(candidates) == 0 {
		return nil, bad("No other topics are available in this exam. You can close it and try another subject.")
	}
	next := pickQuestions(candidates, 1, "practice")[0]
	qs[index] = next
	marked = append(marked, unseenTopic{Prompt: current.Prompt, Topic: topic})
	raw, e = encodeQuestions(qs)
	if e != nil {
		return nil, e
	}
	unseen, e = json.Marshal(marked)
	if e != nil {
		return nil, e
	}
	var answers []*int
	if e = json.Unmarshal(saved, &answers); e != nil {
		return nil, e
	}
	if len(answers) != len(qs) {
		answers = make([]*int, len(qs))
	}
	answers[index] = nil
	saved, e = json.Marshal(answers)
	if e != nil {
		return nil, e
	}
	if _, e = tx.ExecContext(ctx, "UPDATE exam_sessions SET questions=$1,not_studied=$2,saved_answers=$4 WHERE id=$3", string(raw), string(unseen), session, string(saved)); e != nil {
		return nil, e
	}
	if e = tx.Commit(); e != nil {
		return nil, e
	}
	return map[string]any{"questions": qs, "not_studied": marked}, nil
}
