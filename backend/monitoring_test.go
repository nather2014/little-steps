package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestMonitoringWindowAndPercentiles(t *testing.T) {
	m := newMonitoring()
	now := time.Now()
	m.record(metricSample{At: now.Add(-16 * time.Minute), Kind: "api", Millis: 9999, Status: 500})
	for i := 1; i <= 100; i++ {
		m.record(metricSample{At: now, Kind: "api", Route: "/api/profile", Millis: float64(i), Status: 200})
	}
	s := m.snapshot(now)
	api := s["api"].(map[string]any)
	if api["count"] != 100 || api["p95_ms"] != float64(95) || api["server_errors"] != 0 {
		t.Fatalf("Wrong rolling statistics: %v", api)
	}
}
func TestMonitoringBoundedStorage(t *testing.T) {
	m := newMonitoring()
	for i := 0; i < metricCapacity+10; i++ {
		m.record(metricSample{At: time.Now(), Kind: "api", Millis: float64(i)})
	}
	if len(m.samples) != metricCapacity {
		t.Fatal("Sample storage grew past limit")
	}
	if !m.touch("one", time.Now()) || m.touch("one", time.Now()) {
		t.Fatal("Activity writes must be throttled")
	}
}
func TestMonitoringSanitizesPathsAndRecordsFailures(t *testing.T) {
	m := newMonitoring()
	handler := m.wrap(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(400) }))
	handler.ServeHTTP(httptest.NewRecorder(), httptest.NewRequest("GET", "/api/private-email@example.com?token=secret", nil))
	s := m.snapshot(time.Now())
	errors := s["recent_errors"].([]metricSample)
	if len(errors) != 1 || errors[0].Route != "/api/other" || errors[0].Status != 400 {
		t.Fatalf("Unsafe error metadata: %v", errors)
	}
	handler.ServeHTTP(httptest.NewRecorder(), httptest.NewRequest("GET", "/api/admin/metrics", nil))
	if len(m.samples) != 1 {
		t.Fatal("Admin polling should not distort API metrics")
	}
}
