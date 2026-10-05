package main

import (
	"encoding/json"
	"fmt"
	"testing"
)

func TestBorrowingExamples(t *testing.T) {
	bank := map[string][]subject{}
	for g := 2; g <= 10; g++ {
		bank[fmt.Sprint(g)] = []subject{{ID: "maths"}}
	}
	addBorrowingSkills(bank)
	for g, ss := range bank {
		raw, _ := json.Marshal(ss[0].Questions)
		qs, e := parseQuestions(raw)
		if e != nil || len(qs) != 24 {
			t.Fatal(g, e)
		}
		seen := map[string]bool{}
		for _, q := range qs {
			var a, b int
			if _, e = fmt.Sscanf(q.Prompt, "What is %d − %d?", &a, &b); e != nil {
				t.Fatal(e)
			}
			if q.Options[q.Answer] != fmt.Sprint(a-b) || a%10 >= b%10 || q.Explanation == "" || seen[q.Prompt] {
				t.Fatal(q)
			}
			seen[q.Prompt] = true
		}
		snapshot, _ := encodeQuestions(qs)
		again, e := parseQuestions(snapshot)
		if e != nil || again[0].Explanation != qs[0].Explanation {
			t.Fatal("Lost worked steps")
		}
		public, _ := json.Marshal(qs)
		var fields []map[string]any
		json.Unmarshal(public, &fields)
		for _, q := range fields {
			if q["answer"] != nil || q["explanation"] != nil {
				t.Fatal("Hints leaked into tests")
			}
		}
	}
}
