package main

import (
	"fmt"
)

func main() {
	fmt.Println("=================================================")
	fmt.Println("   DISTRIBUTED SYSTEMS - LOGICAL CLOCKS PROJECT")
	fmt.Println("   Lamport Timestamps vs Vector Clocks")
	fmt.Println("=================================================")
	
	// Demo 1: Kør Lamport simulation
	fmt.Println("\n\n### DEMO 1: LAMPORT CLOCK SIMULATION ###")
	lamportSim := NewSimulation(3, false)
	lamportSim.RunScenario()
	
	// Demo 2: Kør Vector clock simulation
	fmt.Println("\n\n### DEMO 2: VECTOR CLOCK SIMULATION ###")
	vectorSim := NewSimulation(3, true)
	vectorSim.RunScenario()
	
	// Demo 3: Vis forskellen i concurrency detection
	DemonstrateConcurrency()
	
	// Demo 4: Kør benchmarks
	fmt.Println("\n\n### DEMO 3: PERFORMANCE BENCHMARK ###")
	result := RunBenchmark(5, 10) // 5 processes, 10 events per process
	CompareResults(result)
	
	// Demo 5: Kør større benchmark
	fmt.Println("\n\n### DEMO 4: SCALABILITY TEST ###")
	fmt.Println("Testing with more processes to show overhead scaling...")
	result2 := RunBenchmark(10, 10) // 10 processes, 10 events per process
	CompareResults(result2)
	
	// Demo 6: Comprehensive Scalability Analysis
	fmt.Println("\n\n### DEMO 5: COMPREHENSIVE SCALABILITY ANALYSIS ###")
	BenchmarkScalability([]int{5, 10, 20, 50, 100}, 10)
	
	// Demo 7: Message Complexity Analysis
	fmt.Println("\n\n### DEMO 6: MESSAGE COMPLEXITY ANALYSIS ###")
	BenchmarkMessageComplexity(100)
	
	// Demo 8: Ordering Capability Measurement
	fmt.Println("\n\n### DEMO 7: ORDERING CAPABILITY MEASUREMENT ###")
	MeasureOrderingCapability(5, 0.7) // 70% concurrency
	
	// Demo 9: Comprehensive Concurrency Testing
	// Note: For detailed concurrency tests, see concurrency_test.go
	fmt.Println("\n\n### DEMO 8: CONCURRENCY LIMITATION DEMONSTRATION ###")
	DemonstrateConcurrentMessages()
	
	fmt.Println("\n\n=================================================")
	fmt.Println("   SIMULATION COMPLETE")
	fmt.Println("=================================================")
	fmt.Println("\nFor detailed analysis and state-of-the-art comparison,")
	fmt.Println("please refer to the README.md documentation.")
}
