package main

import (
	"testing"
)

// Tester Lamport clock funktionalitet
func TestLamportClock(t *testing.T) {
	clock := NewLamportClock()
	
	if clock.GetTime() != 0 {
		t.Errorf("Clock skulle starte ved 0, men er %d", clock.GetTime())
	}
	
	time1 := clock.LocalEvent()
	if time1 != 1 {
		t.Errorf("Første local event skulle være 1, men er %d", time1)
	}
	
	time2 := clock.SendEvent()
	if time2 != 2 {
		t.Errorf("Send event skulle være 2, men er %d", time2)
	}
	
	time3 := clock.ReceiveEvent(1)
	if time3 != 3 {
		t.Errorf("Receive med lavere tid skulle give 3, men gav %d", time3)
	}
	
	time4 := clock.ReceiveEvent(10)
	if time4 != 11 {
		t.Errorf("Receive med højere tid (10) skulle give 11, men gav %d", time4)
	}
}

// Tester vector clock funktionalitet
func TestVectorClock(t *testing.T) {
	// Opret 3 processer
	clock0 := NewVectorClock(3, 0)
	clock1 := NewVectorClock(3, 1)
	
	// Test at alle starter ved [0,0,0]
	vec := clock0.GetVector()
	for i, v := range vec {
		if v != 0 {
			t.Errorf("Vector[%d] skulle være 0, men er %d", i, v)
		}
	}
	
	vec0 := clock0.LocalEvent()
	if vec0[0] != 1 || vec0[1] != 0 || vec0[2] != 0 {
		t.Errorf("Efter local event på P0 forventede [1,0,0], fik %v", vec0)
	}
	
	vec0_send := clock0.SendEvent()
	if vec0_send[0] != 2 {
		t.Errorf("Efter send på P0 skulle P0's counter være 2, men er %d", vec0_send[0])
	}
	

	vec1_recv := clock1.ReceiveEvent(vec0_send)
	// P1 skulle merge [2,0,0] med sin egen [0,0,0] og så inkrementere sin egen
	if vec1_recv[0] != 2 || vec1_recv[1] != 1 || vec1_recv[2] != 0 {
		t.Errorf("Efter receive på P1 forventede [2,1,0], fik %v", vec1_recv)
	}
}

// Tester vector comparison logik
func TestCompareVectors(t *testing.T) {
	// Test: v1 < v2 (v1 happened before v2)
	v1 := []int{1, 2, 3}
	v2 := []int{2, 3, 4}
	if CompareVectors(v1, v2) != -1 {
		t.Errorf("[1,2,3] < [2,3,4] skulle returnere -1")
	}
	
	// Test: v1 > v2 (v2 happened before v1)
	if CompareVectors(v2, v1) != 1 {
		t.Errorf("[2,3,4] > [1,2,3] skulle returnere 1")
	}
	
	// Test: concurrent vectors
	v3 := []int{1, 3, 2}
	v4 := []int{2, 2, 3}
	if CompareVectors(v3, v4) != 0 {
		t.Errorf("[1,3,2] og [2,2,3] er concurrent, skulle returnere 0")
	}
	
	// Test: identiske vectors
	v5 := []int{5, 5, 5}
	v6 := []int{5, 5, 5}
	if CompareVectors(v5, v6) != 0 {
		t.Errorf("Identiske vectors skulle returnere 0")
	}
}

// Tester  happened-before relation for Lamport
func TestLamportHappenedBefore(t *testing.T) {
	clock := NewLamportClock()
	timeA := clock.LocalEvent()
	timeB := clock.LocalEvent()
	if timeA >= timeB {
		t.Errorf("A happened before B, men timeA=%d >= timeB=%d", timeA, timeB)
	}
}

// Test Vector clocks kan detektere concurrency
func TestVectorConcurrency(t *testing.T) {
	clock0 := NewVectorClock(2, 0)
	clock1 := NewVectorClock(2, 1)
	
	// P0 har et event
	vec0 := clock0.LocalEvent() // [1, 0]
	// P1 har et event 
	vec1 := clock1.LocalEvent() // [0, 1]
	
	comparison := CompareVectors(vec0, vec1)
	if comparison != 0 {
		t.Errorf("P0[1,0] og P1[0,1] er concurrent, men comparison returnerede %d", comparison)
	}
}

// Tester causalitet
func TestVectorCausalRelation(t *testing.T) {
	clock0 := NewVectorClock(2, 0)
	clock1 := NewVectorClock(2, 1)
	
	// P0 sender til P1
	vec0 := clock0.SendEvent() // [1, 0]
	
	// P1 modtager fra P0
	vec1 := clock1.ReceiveEvent(vec0) // [1, 1]
	
	// vec0 happened before vec1
	comparison := CompareVectors(vec0, vec1)
	if comparison != -1 {
		t.Errorf("P0's send [1,0] happened before P1's receive [1,1], men comparison=%d", comparison)
	}
}

// Benchmark for Lamport local events
func BenchmarkLamportLocalEvent(b *testing.B) {
	clock := NewLamportClock()
	for i := 0; i < b.N; i++ {
		clock.LocalEvent()
	}
}

// Benchmark for Lamport receive events
func BenchmarkLamportReceive(b *testing.B) {
	clock := NewLamportClock()
	for i := 0; i < b.N; i++ {
		clock.ReceiveEvent(i)
	}
}

// Benchmark for Vector local events
func BenchmarkVectorLocalEvent(b *testing.B) {
	clock := NewVectorClock(10, 0)
	for i := 0; i < b.N; i++ {
		clock.LocalEvent()
	}
}

// Benchmark for Vector receive events
func BenchmarkVectorReceive(b *testing.B) {
	clock := NewVectorClock(10, 0)
	mockVector := make([]int, 10)
	for i := 0; i < b.N; i++ {
		clock.ReceiveEvent(mockVector)
	}
}

// Benchmark for vector comparison
func BenchmarkCompareVectors(b *testing.B) {
	v1 := []int{1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
	v2 := []int{2, 3, 4, 5, 6, 7, 8, 9, 10, 11}
	for i := 0; i < b.N; i++ {
		CompareVectors(v1, v2)
	}
}
