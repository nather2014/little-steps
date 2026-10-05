package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func intp(n int) *int { return &n }
func TestGradeAnswers(t *testing.T) {
	qs := []question{{Prompt: "2 + 2?", Options: []string{"3", "4"}, Answer: 1}, {Prompt: "Opposite of hot?", Options: []string{"Cold", "Warm"}, Answer: 0}}
	correct, review, e := gradeAnswers(qs, []*int{intp(1), intp(1)}, "Basics")
	if e != nil || correct != 1 || len(review) != 2 || review[1].Correct || review[1].Answer != "Cold" {
		t.Fatalf("Incorrect grading: %v %v %v", correct, review, e)
	}
	for _, answers := range [][]*int{{intp(1)}, {nil, intp(0)}, {intp(-1), intp(0)}, {intp(2), intp(0)}} {
		if _, _, e = gradeAnswers(qs, answers, "Basics"); e == nil {
			t.Fatalf("Accepted invalid answers: %v", answers)
		}
	}
}
func TestQuestionResponsesHideAnswer(t *testing.T) {
	raw := []byte(`[["A question",["Yes","No"],1]]`)
	qs, e := parseQuestions(raw)
	if e != nil {
		t.Fatal(e)
	}
	encoded, _ := json.Marshal(qs)
	if strings.Contains(string(encoded), "answer") || qs[0].Answer != 1 {
		t.Fatal("Answer leaked or lost")
	}
}
func TestWeekBoundary(t *testing.T) {
	for _, tt := range []struct{ input, expected string }{{"2026-10-04T18:29:00Z", "2026-09-28"}, {"2026-10-04T18:30:00Z", "2026-10-05"}, {"2026-10-02T12:00:00Z", "2026-09-28"}} {
		now, _ := time.Parse(time.RFC3339, tt.input)
		if got := weekStart(now); got != tt.expected {
			t.Fatalf("%s: got %s, want %s", tt.input, got, tt.expected)
		}
	}
}
func TestRejectCrossOriginWrites(t *testing.T) {
	a := &app{origin: "http://localhost:8090"}
	handler := a.routes(t.TempDir())
	for _, origin := range []string{"", "https://attacker.example"} {
		r := httptest.NewRequest("POST", "/api/rpc/submit_exam", strings.NewReader("{}"))
		r.Header.Set("Origin", origin)
		r.Header.Set("Content-Type", "application/json")
		r.Header.Set("X-Little-Steps", "1")
		w := httptest.NewRecorder()
		handler.ServeHTTP(w, r)
		if w.Code != http.StatusForbidden {
			t.Fatal("Cross-origin write accepted")
		}
	}
}
func TestRateLimitExpires(t *testing.T) {
	l := newRateLimiter()
	now := time.Now()
	for i := 0; i < 30; i++ {
		if !l.allow("test", now) {
			t.Fatal("Unexpected early limit")
		}
	}
	if l.allow("test", now) {
		t.Fatal("Limit missing")
	}
	if !l.allow("test", now.Add(11*time.Minute)) {
		t.Fatal("Limit did not expire")
	}
}
func TestCurriculumAllClasses(t *testing.T) {
	raw, _ := dataFiles.ReadFile("data/curriculum.json")
	var bank map[string][]subject
	if e := json.Unmarshal(raw, &bank); e != nil {
		t.Fatal(e)
	}
	if len(bank) != 12 {
		t.Fatal("Missing classes")
	}
	for g, subjects := range bank {
		if len(subjects) < 3 {
			t.Fatal("Missing subjects for " + g)
		}
		for _, s := range subjects {
			raw, _ := json.Marshal(s.Questions)
			qs, e := parseQuestions(raw)
			if e != nil || len(qs) < 10 {
				t.Fatalf("Invalid class %s %s", g, s.ID)
			}
		}
	}
}

func TestQuestionTopicsAndSnapshots(t *testing.T) {
	raw := []byte("[[\"Count\",[\"1\",\"2\"],1,\"Counting\"]]")
	qs, e := parseQuestions(raw)
	if e != nil {
		t.Fatal(e)
	}
	if qs[0].Topic != "Counting" {
		t.Fatal("Topic lost")
	}
	snapshot, e := encodeQuestions(qs)
	if e != nil {
		t.Fatal(e)
	}
	restored, e := parseQuestions(snapshot)
	if e != nil || restored[0].Answer != 1 {
		t.Fatal("Snapshot lost grading key")
	}
	_, reviews, e := gradeAnswers(restored, []*int{intp(1)}, "Fallback")
	if e != nil || reviews[0].Topic != "Counting" {
		t.Fatal("Review ignored question topic")
	}
}
func TestTopicBalancedWeeklySelection(t *testing.T) {
	pool := []question{}
	for i := 0; i < 15; i++ {
		pool = append(pool, question{Prompt: fmt.Sprint(i), Options: []string{"A", "B"}, Topic: fmt.Sprint(i % 7)})
	}
	picked := pickQuestions(pool, 5, "weekly2026-10-05")
	topics := map[string]bool{}
	for _, q := range picked {
		topics[q.Topic] = true
	}
	if len(topics) != 5 {
		t.Fatal("Selection did not cover distinct topics")
	}
	other := pickQuestions(pool, 5, "weekly2026-10-05")
	for i, q := range picked {
		if q.Prompt != other[i].Prompt {
			t.Fatal("Weekly selection changed")
		}
	}
}
