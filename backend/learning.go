package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"sort"
	"strings"
	"time"
	"unicode/utf8"
)

var reviewDays = []int{1, 3, 7, 14, 30}

const borrowingTopic = "Subtraction with borrowing"

func addBorrowingSkills(bank map[string][]subject) {
	for grade := 2; grade <= 10; grade++ {
		ss := bank[fmt.Sprint(grade)]
		for i := range ss {
			if ss[i].ID != "maths" {
				continue
			}
			for n := 0; n < 12; n++ {
				for _, level := range []string{"easier", "normal"} {
					a := (3+n%5)*10 + n%4
					b := 5 + n%5
					if level == "normal" {
						b += 10
					}
					answer := a - b
					options := []string{fmt.Sprint(answer), fmt.Sprint(answer + 10), fmt.Sprint(answer - 1), fmt.Sprint(answer + 1)}
					shift := n % 4
					options = append(options[shift:], options[:shift]...)
					correct := (4 - shift) % 4
					explanation := fmt.Sprintf("In %d − %d, the ones digit %d is smaller than %d. Exchange one ten for ten ones: %d tens and %d ones. Subtract the ones (%d − %d = %d), then the tens (%d − %d = %d). The answer is %d. Check: %d + %d = %d.", a, b, a%10, b%10, a/10-1, a%10+10, a%10+10, b%10, a%10+10-b%10, a/10-1, b/10, a/10-1-b/10, answer, answer, b, a)
					raw, _ := json.Marshal([]any{fmt.Sprintf("What is %d − %d?", a, b), options, correct, borrowingTopic, map[string]string{"difficulty": level, "explanation": explanation}})
					ss[i].Questions = append(ss[i].Questions, raw)
				}
			}
		}
		bank[fmt.Sprint(grade)] = ss
	}
}
func recordLearning(ctx context.Context, tx *sql.Tx, a attempt) error {
	counts := map[string][2]int{}
	for _, q := range a.Review {
		c := counts[q.Topic]
		c[1]++
		if q.Correct {
			c[0]++
		}
		counts[q.Topic] = c
	}
	topics := []string{}
	for topic := range counts {
		topics = append(topics, topic)
	}
	sort.Strings(topics)
	for _, topic := range topics {
		c := counts[topic]
		accuracy := 100 * c[0] / c[1]
		var stage int
		var due time.Time
		err := tx.QueryRowContext(ctx, "SELECT stage,due_at FROM learning_skills WHERE student_id=$1 AND subject=$2 AND topic=$3 FOR UPDATE", a.Student, a.Subject, topic).Scan(&stage, &due)
		if err != nil && !errors.Is(err, sql.ErrNoRows) {
			return err
		}
		if accuracy < 80 {
			stage = 0
		} else if err == nil && !a.Date.Before(due) && stage < 4 {
			stage++
		}
		next := a.Date.AddDate(0, 0, reviewDays[stage])
		// Early successful practice keeps the already scheduled review date.
		if err == nil && accuracy >= 80 && a.Date.Before(due) {
			next = due
		}
		_, err = tx.ExecContext(ctx, "INSERT INTO learning_skills(student_id,subject,topic,correct,total,last_accuracy,stage,due_at,updated_at) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT(student_id,subject,topic) DO UPDATE SET correct=learning_skills.correct+excluded.correct,total=learning_skills.total+excluded.total,last_accuracy=excluded.last_accuracy,needs_help=(excluded.last_accuracy<80),stage=excluded.stage,due_at=excluded.due_at,updated_at=excluded.updated_at", a.Student, a.Subject, topic, c[0], c[1], accuracy, stage, next, a.Date)
		if err != nil {
			return err
		}
	}
	for _, q := range a.NotStudied {
		_, err := tx.ExecContext(ctx, "INSERT INTO learning_skills(student_id,subject,topic,last_accuracy,due_at) VALUES($1,$2,$3,0,$4) ON CONFLICT(student_id,subject,topic) DO UPDATE SET needs_help=true,stage=0,due_at=LEAST(learning_skills.due_at,excluded.due_at)", a.Student, a.Subject, q.Topic, a.Date)
		if err != nil {
			return err
		}
	}

	return nil
}
func (a *app) learning(ctx context.Context, p actor, id string) (any, error) {
	if id == "" {
		id = p.ID
	}
	if e := a.canRead(ctx, p, id); e != nil {
		return nil, e
	}
	var grade int
	if e := a.db.QueryRowContext(ctx, "SELECT grade FROM profiles WHERE id=$1", id).Scan(&grade); e != nil {
		return nil, e
	}
	rows, e := a.db.QueryContext(ctx, "SELECT subject,topic,correct,total,last_accuracy,stage,due_at,needs_help FROM learning_skills WHERE student_id=$1 ORDER BY due_at,subject,topic", id)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	skills := []map[string]any{}
	now := time.Now()
	for rows.Next() {
		var subject, topic string
		var correct, total, accuracy, stage int
		var due time.Time
		var needsHelp bool
		if e = rows.Scan(&subject, &topic, &correct, &total, &accuracy, &stage, &due, &needsHelp); e != nil {
			return nil, e
		}
		skills = append(skills, map[string]any{"subject": subject, "topic": topic, "correct": correct, "total": total, "last_accuracy": accuracy, "stage": stage, "due_at": due, "due": !now.Before(due), "weak": accuracy < 80 || needsHelp, "review_days": reviewDays[stage]})
	}
	if e = rows.Err(); e != nil {
		return nil, e
	}
	catalog := []map[string]any{}
	for _, sub := range a.bank[fmt.Sprint(grade)] {
		raw, _ := json.Marshal(sub.Questions)
		qs, e := parseQuestions(raw)
		if e != nil {
			return nil, e
		}
		topics := map[string]int{}
		for _, q := range qs {
			topics[q.Topic]++
		}
		names := []string{}
		for topic := range topics {
			names = append(names, topic)
		}
		sort.Strings(names)
		for _, topic := range names {
			catalog = append(catalog, map[string]any{"subject": sub.ID, "subject_name": sub.Name, "topic": topic, "questions": topics[topic]})
		}
	}
	notes := []map[string]any{}
	nr, e := a.db.QueryContext(ctx, "SELECT n.attempt_id,n.question_index,n.reason,n.note FROM mistake_notes n JOIN attempts a ON a.id=n.attempt_id WHERE a.student_id=$1", id)
	if e != nil {
		return nil, e
	}
	defer nr.Close()
	for nr.Next() {
		var attemptID int64
		var index int
		var reason, note string
		if e = nr.Scan(&attemptID, &index, &reason, &note); e != nil {
			return nil, e
		}
		notes = append(notes, map[string]any{"attempt_id": attemptID, "index": index, "reason": reason, "note": note})
	}
	if e = nr.Err(); e != nil {
		return nil, e
	}
	return map[string]any{"skills": skills, "catalog": catalog, "notes": notes, "review_intervals": reviewDays}, nil
}
func (a *app) skillPool(grade int, subjectID, topic string) ([]question, []question, error) {
	for _, s := range a.bank[fmt.Sprint(grade)] {
		if s.ID != subjectID {
			continue
		}
		raw, _ := json.Marshal(s.Questions)
		pool, e := parseQuestions(raw)
		if e != nil {
			return nil, nil, e
		}
		focus := []question{}
		for _, q := range pool {
			if q.Topic == topic {
				focus = append(focus, q)
			}
		}
		if len(focus) == 0 {
			return nil, nil, bad("This topic is not available for your class")
		}
		return focus, pool, nil
	}
	return nil, nil, bad("Choose a subject for your class")
}
func (a *app) lesson(ctx context.Context, p actor, id, subjectID, topic string) (any, error) {
	if id == "" {
		id = p.ID
	}
	if e := a.canRead(ctx, p, id); e != nil {
		return nil, e
	}
	var grade int
	if e := a.db.QueryRowContext(ctx, "SELECT grade FROM profiles WHERE id=$1", id).Scan(&grade); e != nil {
		return nil, e
	}
	focus, _, e := a.skillPool(grade, subjectID, topic)
	if e != nil {
		return nil, e
	}
	examples := []map[string]any{}
	for i, q := range focus {
		if i >= 2 {
			break
		}
		examples = append(examples, map[string]any{"prompt": q.Prompt, "answer": q.Options[q.Answer], "explanation": q.Explanation})
	}
	steps := conceptSteps(subjectID, topic)
	return map[string]any{"subject": subjectID, "topic": topic, "steps": steps, "examples": examples, "has_worked_steps": focus[0].Explanation != ""}, nil
}
func conceptSteps(subjectID, topic string) []string {
	switch topic {
	case borrowingTopic:
		return []string{"Line up tens and ones. Start in the ones column.", "If there are too few ones, exchange one ten for ten ones. Reduce the tens by one.", "Subtract the ones, then subtract the tens. Check by adding your answer to the number you took away."}
	case "Addition":
		return []string{"Add means combine groups. Line up the digits by place value.", "Add from the ones column. If a column reaches ten, exchange ten ones for one ten.", "Check whether your answer is reasonable by estimating or using subtraction."}
	case "Subtraction":
		return []string{"Subtract means take away or find a difference.", "Line up place values and start with the ones. Regroup when there are too few ones.", "Check your answer by addition: answer + amount taken away = starting amount."}
	case "Fractions", "Fractions in stories":
		return []string{"A fraction describes equal parts of a whole. The denominator counts all equal parts; the numerator counts chosen parts.", "Draw the whole split into equal parts and shade the parts you need.", "When comparing, first check whether the wholes and the size of each part are the same."}
	case "Area":
		return []string{"Area measures the space inside a shape, using square units.", "For a rectangle, multiply length by width.", "Write square units and check you did not add the side lengths instead."}
	case "Perimeter":
		return []string{"Perimeter is the distance all the way around a shape.", "Add every outside side. A rectangle has two lengths and two widths.", "Use length units, such as cm, rather than square units."}
	case "Equal groups", "Sharing equally":
		return []string{"Multiplication combines equal groups; division shares into equal groups.", "Draw the groups or use counters. Count how many are in each group and how many groups there are.", "Check a division using multiplication."}
	}
	if subjectID == "english" {
		return []string{"Read the whole sentence or short passage aloud. Notice the words around the gap.", "Say why your choice fits the meaning and the language rule. If the rule is new, ask a teacher or grown-up to explain it with an example.", "Close the example and make a new sentence using the same idea."}
	}
	if subjectID == "maths" || subjectID == "olympiad_maths" || subjectID == "olympiad_reasoning" {
		return []string{"Identify what is given and what you need to find. Draw a picture or write the pattern.", "Use your textbook or teacher's explanation for this topic, then follow the example below.", "Explain each step in your own words. Check using a different method before trying independently."}
	}
	return []string{"Use your textbook or a teacher's explanation to understand this topic first.", "Connect the idea to an everyday example. Explain why the example answer makes sense.", "Close the book and explain the idea to someone in one or two simple sentences."}
}
func (a *app) targetedPractice(ctx context.Context, p actor, subjectID, topic string) (any, error) {
	if e := student(p); e != nil {
		return nil, e
	}
	focus, pool, e := a.skillPool(*p.Profile.Grade, subjectID, topic)
	if e != nil {
		return nil, e
	}
	picked := []question{}
	if topic == borrowingTopic {
		easy, normal := []question{}, []question{}
		for _, q := range focus {
			if q.Difficulty == "easier" {
				easy = append(easy, q)
			} else {
				normal = append(normal, q)
			}
		}
		picked = append(pickQuestions(easy, 5, "practice"), pickQuestions(normal, 5, "practice")...)
	} else {
		picked = pickQuestions(focus, 10, "practice")
	}
	focusCount := len(picked)
	if len(picked) < 10 {
		others := []question{}
		for _, q := range pool {
			if q.Topic != topic {
				others = append(others, q)
			}
		}
		picked = append(picked, pickQuestions(others, 10-len(picked), "practice")...)
	}
	if len(picked) != 10 {
		return nil, bad("There are not enough questions for this practice set")
	}
	_, e = a.availableExams(ctx, p)
	if e != nil {
		return nil, e
	}
	var examID int64
	if e = a.db.QueryRowContext(ctx, "SELECT id FROM exams WHERE grade=$1 AND subject=$2 AND week_start=$3", *p.Profile.Grade, subjectID, weekStart(time.Now())).Scan(&examID); e != nil {
		return nil, e
	}
	snapshot, e := encodeQuestions(picked)
	if e != nil {
		return nil, e
	}
	session := randomID()
	deadline := time.Now().Add(15 * time.Minute)
	_, e = a.db.ExecContext(ctx, "INSERT INTO exam_sessions(id,student_id,exam_id,mode,questions,deadline_at) VALUES($1,$2,$3,'practice',$4,$5)", session, p.ID, examID, string(snapshot), deadline)
	return map[string]any{"session_id": session, "title": "Focused practice: " + topic, "topic": topic, "questions": picked, "answers": make([]*int, 10), "deadline_at": deadline, "server_now": time.Now(), "focus_count": focusCount, "mixed_count": 10 - focusCount}, e
}
func (a *app) mistakeNote(ctx context.Context, p actor, id int64, index int, reason, note string) (any, error) {
	if e := student(p); e != nil {
		return nil, e
	}
	if index < 0 || !map[string]bool{"concept": true, "calculation": true, "reading": true, "unsure": true, "other": true}[reason] || reason == "" || utf8.RuneCountInString(note) > 500 {
		return nil, bad("Choose a reason and keep the note under 500 characters")
	}
	tx, e := a.db.BeginTx(ctx, nil)
	if e != nil {
		return nil, e
	}
	defer tx.Rollback()
	var raw []byte
	var subjectID string
	e = tx.QueryRowContext(ctx, "SELECT review,subject FROM attempts WHERE id=$1 AND student_id=$2", id, p.ID).Scan(&raw, &subjectID)
	if errors.Is(e, sql.ErrNoRows) {
		return nil, forbidden()
	}
	if e != nil {
		return nil, e
	}
	var review []review
	if e = json.Unmarshal(raw, &review); e != nil {
		return nil, e
	}
	if index >= len(review) {
		return nil, bad("Choose a valid question")
	}
	_, e = tx.ExecContext(ctx, "INSERT INTO mistake_notes(attempt_id,question_index,reason,note) VALUES($1,$2,$3,$4) ON CONFLICT(attempt_id,question_index) DO UPDATE SET reason=excluded.reason,note=excluded.note,updated_at=now()", id, index, reason, strings.TrimSpace(note))
	if e != nil {
		return nil, e
	}
	_, e = tx.ExecContext(ctx, "UPDATE learning_skills SET needs_help=true,stage=0,due_at=LEAST(due_at,now()+interval '1 day') WHERE student_id=$1 AND subject=$2 AND topic=$3", p.ID, subjectID, review[index].Topic)
	if e != nil {
		return nil, e
	}
	return map[string]any{"saved": true}, tx.Commit()
}

// Interleave up to three weak or due skills with the broader subject pool.
func (a *app) rankedQuestions(ctx context.Context, id, subjectID string, pool []question) ([]question, error) {
	rows, e := a.db.QueryContext(ctx, "SELECT topic FROM learning_skills WHERE student_id=$1 AND subject=$2 AND (last_accuracy<80 OR needs_help OR due_at<=now()) ORDER BY last_accuracy,due_at LIMIT 3", id, subjectID)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	selected := []question{}
	used := map[string]bool{}
	for rows.Next() {
		var topic string
		if e = rows.Scan(&topic); e != nil {
			return nil, e
		}
		focus := []question{}
		for _, q := range pool {
			if q.Topic == topic && !used[q.Prompt] {
				focus = append(focus, q)
			}
		}
		if len(focus) > 0 {
			q := pickQuestions(focus, 1, "practice")[0]
			selected = append(selected, q)
			used[q.Prompt] = true
		}
	}
	if e = rows.Err(); e != nil {
		return nil, e
	}
	remaining := []question{}
	for _, q := range pool {
		if !used[q.Prompt] {
			remaining = append(remaining, q)
		}
	}
	selected = append(selected, pickQuestions(remaining, 10-len(selected), randomID())...)
	return selected, nil
}
