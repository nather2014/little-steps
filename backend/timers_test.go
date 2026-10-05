package main

import "testing"

func TestTimedAnswers(t *testing.T) {
	qs := []question{{Prompt: "One", Options: []string{"A", "B"}, Answer: 0}, {Prompt: "Two", Options: []string{"A", "B"}, Answer: 1}}
	correct, review, err := gradeTimedAnswers(qs, []*int{intp(0), nil}, "Maths", true)
	if err != nil || correct != 1 || len(review) != 2 || review[1].Selected != "Not answered" || review[1].Correct {
		t.Fatalf("bad partial grade: %v %v %v", correct, review, err)
	}
	if _, _, err = gradeTimedAnswers(qs, []*int{intp(3), nil}, "Maths", true); err == nil {
		t.Fatal("accepted invalid answer")
	}
	for _, tt := range []struct {
		subject, category string
		seconds           int
	}{{"maths", "regular", 900}, {"olympiad_maths", "olympiad", 1200}, {"olympiad_reasoning", "olympiad", 1200}} {
		c, s := examSettings(tt.subject)
		if c != tt.category || s != tt.seconds {
			t.Fatal(tt)
		}
	}
}
