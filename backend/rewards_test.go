package main

import (
	"testing"
	"time"
)

func TestLearningPeriods(t *testing.T) {
	cases := []struct{ now, day, week string }{
		{"2026-10-04T18:29:59Z", "2026-10-04", "2026-09-28"},
		{"2026-10-04T18:30:00Z", "2026-10-05", "2026-10-05"},
		{"2026-10-05T18:30:00Z", "2026-10-06", "2026-10-05"},
	}
	for _, c := range cases {
		n, _ := time.Parse(time.RFC3339, c.now)
		day, end, week, weekEnd := learningPeriods(n)
		if day.Format("2006-01-02") != c.day || week.Format("2006-01-02") != c.week {
			t.Fatalf("Wrong periods at %s", c.now)
		}
		if end.Sub(day) != 24*time.Hour || weekEnd.Sub(week) != 7*24*time.Hour {
			t.Fatal("Wrong reset interval")
		}
	}
}
func TestLevelsAndRankBoundaries(t *testing.T) {
	level, into, name := levelInfo(500)
	if level != 2 || into != 0 || name != "Sprout" {
		t.Fatal("Wrong level threshold")
	}
	for _, c := range []struct {
		points int
		name   string
		rr     int
	}{{0, "Iron 1", 0}, {99, "Iron 1", 99}, {100, "Iron 2", 0}, {299, "Iron 3", 99}, {300, "Bronze 1", 0}, {900, "Gold 1", 0}, {2399, "Immortal 3", 99}, {2400, "Radiant", 0}} {
		rank := rankInfo(c.points)
		if rank["name"] != c.name || rank["rr"] != c.rr {
			t.Fatalf("Wrong rank for %d: %v", c.points, rank)
		}
	}
	for _, c := range []struct{ correct, want int }{{5, 30}, {4, 20}, {3, 10}, {2, -10}, {1, -20}, {0, -20}} {
		if scoreRR(c.correct, 5) != c.want {
			t.Fatal("Wrong RR rule")
		}
	}
}
