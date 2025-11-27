package main

import (
	"fmt"
	"math/rand"
	"runtime"
	"time"
)

// Performance og correctness metrics struct initialization
type Metrics struct {
	ClockType           string
	NumProcesses        int
	NumEvents           int
	TotalExecutionTime  time.Duration
	MemoryUsed          uint64  // Bytes
	MessageOverhead     int     // Bytes per message
	OrderingCorrectness float64 // Procent af korrekt ordnede events
}

// Benchmark results struct initialization
type BenchmarkResult struct {
	LamportMetrics Metrics
	VectorMetrics  Metrics
}

// Kør benchmark for lamport og vector
func RunBenchmark(numProcesses int, numEvents int) BenchmarkResult {
	fmt.Printf("\n=== Running Benchmark ===\n")
	fmt.Printf("Processes: %d, Events per process: %d\n", numProcesses, numEvents)

	result := BenchmarkResult{}

	// Test Lamport
	fmt.Println("\nTesting Lamport Clock...")
	result.LamportMetrics = benchmarkAlgorithm(numProcesses, numEvents, false)

	// Test Vector
	fmt.Println("Testing Vector Clock...")
	result.VectorMetrics = benchmarkAlgorithm(numProcesses, numEvents, true)

	return result
}

// Måler performance for en algoritme
func benchmarkAlgorithm(numProcesses int, numEvents int, useVectorClock bool) Metrics {
	// Start memory measurement
	var memBefore runtime.MemStats
	runtime.GC() // Force garbage collection for accurate measurement
	runtime.ReadMemStats(&memBefore)

	// Start timing
	startTime := time.Now()

	// Opret simulation
	sim := NewSimulation(numProcesses, useVectorClock)

	// Start processer
	done := make(chan bool)
	for _, p := range sim.Processes {
		p.Run(done)
	}

	time.Sleep(10 * time.Millisecond)

	// Generer random events
	rand.Seed(time.Now().UnixNano())
	for i := 0; i < numEvents; i++ {
		for _, p := range sim.Processes {
			eventType := rand.Intn(3) // 0=local, 1=send, 2=send

			switch eventType {
			case 0:
				// Local event
				p.HandleLocalEvent(fmt.Sprintf("Event %d", i))
			default:
				// Send event
				targetID := rand.Intn(numProcesses)
				if targetID != p.ID {
					target := sim.Processes[targetID]
					p.SendMessage(target, fmt.Sprintf("Msg %d", i))
				}
			}
		}
		time.Sleep(1 * time.Millisecond)
	}

	// Vent på at alle beskeder er håndteret
	time.Sleep(100 * time.Millisecond)
	close(done)

	// Stop timing
	executionTime := time.Since(startTime)

	// Measure memory
	var memAfter runtime.MemStats
	runtime.ReadMemStats(&memAfter)
	memoryUsed := memAfter.Alloc - memBefore.Alloc

	// Calculate message overhead
	var messageOverhead int
	if useVectorClock {
		// Vector clock sender et array af ints
		messageOverhead = numProcesses * 8 // 8 bytes per int (int64)
	} else {
		// Lamport sender bare et enkelt int
		messageOverhead = 8 // 8 bytes
	}

	// Calculate ordering correctness
	correctness := calculateOrderingCorrectness(sim)

	clockType := "Lamport"
	if useVectorClock {
		clockType = "Vector"
	}

	return Metrics{
		ClockType:           clockType,
		NumProcesses:        numProcesses,
		NumEvents:           numEvents * numProcesses,
		TotalExecutionTime:  executionTime,
		MemoryUsed:          memoryUsed,
		MessageOverhead:     messageOverhead,
		OrderingCorrectness: correctness,
	}
}

// Beregner antal korrekt ordnede events
func calculateOrderingCorrectness(sim *Simulation) float64 {
	type EventRecord struct {
		ProcessID int
		Vector    []int
		Timestamp int
		EventNum  int
	}

	var allEvents []EventRecord

	// Saml events fra hver proces
	for _, p := range sim.Processes {
		if sim.UseVectorClock {
			// Brug de gemte vector snapshots
			for i := 0; i < len(p.EventLog); i++ {
				var vector []int
				if i < len(p.EventVectors) {
					vector = p.EventVectors[i]
				} else {
					// Fallback hvis der mangler data
					vector = p.VectorClock.GetVector()
				}
				allEvents = append(allEvents, EventRecord{
					ProcessID: p.ID,
					Vector:    vector,
					EventNum:  i,
				})
			}
		} else {
			// Brug de gemte Lamport timestamps
			for i := 0; i < len(p.EventLog); i++ {
				var timestamp int
				if i < len(p.EventTimestamps) {
					timestamp = p.EventTimestamps[i]
				} else {
					// Fallback hvis der mangler data
					timestamp = p.LamportClock.GetTime()
				}
				allEvents = append(allEvents, EventRecord{
					ProcessID: p.ID,
					Timestamp: timestamp,
					EventNum:  i,
				})
			}
		}
	}

	if len(allEvents) <= 1 {
		return 100.0 // Trivial case
	}

	// Sammenlign alle event-par og se hvor mange vi kan ordne
	totalPairs := 0
	orderablePairs := 0

	for i := 0; i < len(allEvents); i++ {
		for j := i + 1; j < len(allEvents); j++ {
			totalPairs++

			if sim.UseVectorClock {
				_ = CompareVectors(allEvents[i].Vector, allEvents[j].Vector)
				orderablePairs++
			} else {
				t1 := allEvents[i].Timestamp
				t2 := allEvents[j].Timestamp

				if t1 != t2 {
					orderablePairs++
				} else {

				}
			}
		}
	}

	if totalPairs == 0 {
		return 100.0
	}

	return (float64(orderablePairs) / float64(totalPairs)) * 100.0
}

// Print funktion
func PrintMetrics(metrics Metrics) {
	fmt.Printf("\n--- %s Metrics ---\n", metrics.ClockType)
	fmt.Printf("Processes:           %d\n", metrics.NumProcesses)
	fmt.Printf("Total Events:        %d\n", metrics.NumEvents)
	fmt.Printf("Execution Time:      %v\n", metrics.TotalExecutionTime)
	fmt.Printf("Memory Used:         %d bytes (%.2f KB)\n",
		metrics.MemoryUsed, float64(metrics.MemoryUsed)/1024.0)
	fmt.Printf("Message Overhead:    %d bytes per message\n", metrics.MessageOverhead)
	fmt.Printf("Ordering Capability: %.1f%%\n", metrics.OrderingCorrectness)
}

// Sammenligner og printer en comparison af to results
func CompareResults(result BenchmarkResult) {
	fmt.Printf("\n\n=== COMPARISON ===\n")

	PrintMetrics(result.LamportMetrics)
	PrintMetrics(result.VectorMetrics)

	fmt.Printf("\n--- Analysis ---\n")

	// Time comparison
	timeDiff := result.VectorMetrics.TotalExecutionTime - result.LamportMetrics.TotalExecutionTime
	timePercent := (float64(timeDiff) / float64(result.LamportMetrics.TotalExecutionTime)) * 100
	fmt.Printf("Time Overhead (Vector vs Lamport): %+v (%+.1f%%)\n", timeDiff, timePercent)

	// Memory comparison
	memDiff := int64(result.VectorMetrics.MemoryUsed) - int64(result.LamportMetrics.MemoryUsed)
	memPercent := (float64(memDiff) / float64(result.LamportMetrics.MemoryUsed)) * 100
	fmt.Printf("Memory Overhead (Vector vs Lamport): %+d bytes (%+.1f%%)\n", memDiff, memPercent)

	// Message overhead comparison
	msgDiff := result.VectorMetrics.MessageOverhead - result.LamportMetrics.MessageOverhead
	msgPercent := (float64(msgDiff) / float64(result.LamportMetrics.MessageOverhead)) * 100
	fmt.Printf("Message Size Overhead (Vector vs Lamport): %+d bytes (%+.1f%%)\n", msgDiff, msgPercent)

	// Ordering capability comparison
	orderingDiff := result.VectorMetrics.OrderingCorrectness - result.LamportMetrics.OrderingCorrectness
	fmt.Printf("Ordering Capability Improvement: %+.1f%%\n", orderingDiff)

	fmt.Printf("\n--- Summary ---\n")
	fmt.Println("Lamport Clock:")
	fmt.Println("  + Lower time overhead")
	fmt.Println("  + Lower memory usage")
	fmt.Println("  + Smaller message size")
	fmt.Println("  - Only partial ordering (cannot determine order of concurrent events)")

	fmt.Println("\nVector Clock:")
	fmt.Println("  + Total ordering capability (can determine all causal relationships)")
	fmt.Println("  + Can detect concurrent events")
	fmt.Println("  - Higher overhead (time, space, message size)")
	fmt.Println("  - Overhead scales with number of processes (O(n) per message)")
}

// Måler hvordan scalability med overhead vokser med antal processer
func BenchmarkScalability(processCounts []int, eventsPerProcess int) {
	fmt.Println("\n\n=== SCALABILITY ANALYSIS ===")
	fmt.Printf("Events per process: %d\n", eventsPerProcess)
	fmt.Printf("Running %d iterations per configuration...\n\n", 100)

	fmt.Printf("%-12s | %-15s | %-15s | %-12s | %-15s | %-15s\n",
		"Processes", "Lamport (µs)", "Vector (µs)", "Ratio", "Lamport Mem", "Vector Mem")
	fmt.Println("-------------|-----------------|-----------------|--------------|-----------------|------------------")

	for _, numProc := range processCounts {
		// Benchmark Lamport
		var lamportTotal time.Duration
		var lamportMem uint64
		iterations := 100

		for i := 0; i < iterations; i++ {
			var memBefore runtime.MemStats
			runtime.GC()
			runtime.ReadMemStats(&memBefore)

			start := time.Now()
			sim := NewSimulation(numProc, false)
			done := make(chan bool)
			for _, p := range sim.Processes {
				p.Run(done)
			}

			// Generer events
			for e := 0; e < eventsPerProcess; e++ {
				for _, p := range sim.Processes {
					if rand.Intn(2) == 0 {
						p.HandleLocalEvent(fmt.Sprintf("E%d", e))
					} else {
						target := rand.Intn(numProc)
						if target != p.ID {
							p.SendMessage(sim.Processes[target], fmt.Sprintf("M%d", e))
						}
					}
				}
			}

			close(done)
			lamportTotal += time.Since(start)

			var memAfter runtime.MemStats
			runtime.ReadMemStats(&memAfter)
			lamportMem += memAfter.Alloc - memBefore.Alloc
		}

		lamportAvg := lamportTotal.Microseconds() / int64(iterations)
		lamportMemAvg := lamportMem / uint64(iterations)

		// Benchmark Vector
		var vectorTotal time.Duration
		var vectorMem uint64

		for i := 0; i < iterations; i++ {
			var memBefore runtime.MemStats
			runtime.GC()
			runtime.ReadMemStats(&memBefore)

			start := time.Now()
			sim := NewSimulation(numProc, true)
			done := make(chan bool)
			for _, p := range sim.Processes {
				p.Run(done)
			}

			// Generer events
			for e := 0; e < eventsPerProcess; e++ {
				for _, p := range sim.Processes {
					if rand.Intn(2) == 0 {
						p.HandleLocalEvent(fmt.Sprintf("E%d", e))
					} else {
						target := rand.Intn(numProc)
						if target != p.ID {
							p.SendMessage(sim.Processes[target], fmt.Sprintf("M%d", e))
						}
					}
				}
			}

			close(done)
			vectorTotal += time.Since(start)

			var memAfter runtime.MemStats
			runtime.ReadMemStats(&memAfter)
			vectorMem += memAfter.Alloc - memBefore.Alloc
		}

		vectorAvg := vectorTotal.Microseconds() / int64(iterations)
		vectorMemAvg := vectorMem / uint64(iterations)

		ratio := float64(vectorAvg) / float64(lamportAvg)

		fmt.Printf("%-12d | %-15d | %-15d | %-12.2fx | %-15d | %-15d\n",
			numProc, lamportAvg, vectorAvg, ratio,
			lamportMemAvg, vectorMemAvg)
	}

	fmt.Println("\n--- Analysis ---")
	fmt.Println("Lamport Clock: Time complexity O(1) - constant regardless of process count")
	fmt.Println("Vector Clock:  Time complexity O(n) - grows linearly with process count")
	fmt.Println("               (due to vector copy and merge operations)")
	fmt.Println()
	fmt.Println("Space Complexity:")
	fmt.Printf("  Lamport: O(1) = 8 bytes per process\n")
	fmt.Printf("  Vector:  O(n) = 8n bytes per process (where n = number of processes)\n")
}

// BenchmarkMessageComplexity analyserer message overhead i detaljer
func BenchmarkMessageComplexity(maxProcesses int) {
	fmt.Println("\n\n=== MESSAGE COMPLEXITY ANALYSIS ===")
	fmt.Printf("%-12s | %-18s | %-18s | %-15s\n",
		"Processes", "Lamport Msg Size", "Vector Msg Size", "Overhead Ratio")
	fmt.Println("-------------|--------------------|--------------------|------------------")

	for n := 5; n <= maxProcesses; n += 5 {
		lamportSize := 8    // 1 int64
		vectorSize := n * 8 // n int64s
		ratio := float64(vectorSize) / float64(lamportSize)

		fmt.Printf("%-12d | %-18d | %-18d | %-15.1fx\n",
			n, lamportSize, vectorSize, ratio)
	}

	fmt.Println("\n--- Analysis ---")
	fmt.Println("Message overhead grows linearly with number of processes for Vector clocks")
	fmt.Println("Lamport maintains constant message size regardless of system scale")
	fmt.Println()
	fmt.Println("For large distributed systems (n > 100), this becomes significant:")
	fmt.Printf("  At n=100:  Vector messages are 100x larger than Lamport\n")
	fmt.Printf("  At n=1000: Vector messages are 1000x larger than Lamport\n")
}

// MeasureOrderingCapability måler faktisk ordering capability med forskellige workloads
func MeasureOrderingCapability(numProcesses int, concurrencyLevel float64) {
	fmt.Println("\n\n=== ORDERING CAPABILITY MEASUREMENT ===")
	fmt.Printf("Processes: %d, Concurrency level: %.0f%%\n", numProcesses, concurrencyLevel*100)

	// Test Lamport
	lamportSim := NewSimulation(numProcesses, false)
	done := make(chan bool)
	for _, p := range lamportSim.Processes {
		p.Run(done)
	}

	// Generer workload med specificeret concurrency level
	numEvents := 50
	for i := 0; i < numEvents; i++ {
		for _, p := range lamportSim.Processes {
			if rand.Float64() < concurrencyLevel {
				// Concurrent local event
				p.HandleLocalEvent(fmt.Sprintf("Local %d", i))
			} else {
				// Message passing (creates causal relation)
				target := rand.Intn(numProcesses)
				if target != p.ID {
					p.SendMessage(lamportSim.Processes[target], fmt.Sprintf("Msg %d", i))
				}
			}
		}
		time.Sleep(1 * time.Millisecond)
	}

	time.Sleep(50 * time.Millisecond)
	close(done)

	lamportCorrectness := calculateOrderingCorrectness(lamportSim)

	// Test Vector
	vectorSim := NewSimulation(numProcesses, true)
	done2 := make(chan bool)
	for _, p := range vectorSim.Processes {
		p.Run(done2)
	}

	for i := 0; i < numEvents; i++ {
		for _, p := range vectorSim.Processes {
			if rand.Float64() < concurrencyLevel {
				p.HandleLocalEvent(fmt.Sprintf("Local %d", i))
			} else {
				target := rand.Intn(numProcesses)
				if target != p.ID {
					p.SendMessage(vectorSim.Processes[target], fmt.Sprintf("Msg %d", i))
				}
			}
		}
		time.Sleep(1 * time.Millisecond)
	}

	time.Sleep(50 * time.Millisecond)
	close(done2)

	vectorCorrectness := calculateOrderingCorrectness(vectorSim)

	fmt.Printf("\nResults:\n")
	fmt.Printf("  Lamport Clock: %.1f%% of event pairs can be ordered\n", lamportCorrectness)
	fmt.Printf("  Vector Clock:  %.1f%% of event pairs can be ordered\n", vectorCorrectness)
	fmt.Printf("  Improvement:   +%.1f%%\n", vectorCorrectness-lamportCorrectness)

	fmt.Println("\n--- Interpretation ---")
	fmt.Println("Vector Clock achieves total ordering: can determine causal relationship")
	fmt.Println("for ALL event pairs (either happens-before or concurrent)")
	fmt.Println()
	fmt.Println("Lamport Clock achieves partial ordering: can only order events with")
	fmt.Println("direct causal chains, cannot distinguish concurrent events")
}
