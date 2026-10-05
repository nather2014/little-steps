package main

import (
	"encoding/json"
	"testing"
)

func TestTrialScoring(t *testing.T) {
	streak := 0
	for i, want := range []int{10, 12, 14, 16, 18, 20, 20} {
		points, next := trialPoints(true, streak)
		if points != want || next != i+1 {
			t.Fatalf("Wrong combo: %d %d", points, next)
		}
		streak = next
	}
	points, streak := trialPoints(false, streak)
	if points != 0 || streak != 0 {
		t.Fatal("Wrong answers must reset the streak")
	}
	points, streak = trialPoints(true, streak)
	if points != 10 || streak != 1 {
		t.Fatal("Streak did not restart")
	}
}
func TestTrialQuestionStateHidesFutureAnswers(t *testing.T) {
	qs := []question{{Prompt: "First", Options: []string{"a", "b"}, Answer: 1, Explanation: "Secret worked step"}, {Prompt: "Second", Options: []string{"a", "b"}, Answer: 0}}
	state := trialState(trial{Pool: qs})
	raw, _ := json.Marshal(state)
	var result map[string]json.RawMessage
	json.Unmarshal(raw, &result)
	var q map[string]any
	json.Unmarshal(result["question"], &q)
	if q["answer"] != nil || q["explanation"] != nil || result["pool"] != nil {
		t.Fatal("Answers leaked")
	}
	t1 := trial{Pool: qs, Answers: []trialAnswer{{}, {}, {}}}
	if trialState(t1)["question"].(question).Prompt != "Second" {
		t.Fatal("Question pool must cycle only after exhaustion")
	}
}
