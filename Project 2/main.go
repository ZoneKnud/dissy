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

	// Demo 3: Concurrent Message Arrival
	// Viser hvad der sker når 2 beskeder ankommer med samme Lamport timestamp
	fmt.Println("\n\n### DEMO 3: CONCURRENT MESSAGE ARRIVAL ###")
	fmt.Println("(This demonstrates Lamport's fundamental limitation)")
	DemonstrateConcurrentMessages()

	// Demo 4: Comprehensive Scalability Analysis
	// Måler O(1) vs O(n) kompleksitet med 5-100 processer
	fmt.Println("\n\n### DEMO 4: SCALABILITY ANALYSIS ###")
	fmt.Println("(Measuring O(1) vs O(n) complexity with increasing process count)")
	BenchmarkScalability([]int{5, 10, 20, 50}, 10)

	// Demo 5: Message Complexity Analysis
	// Viser hvordan message size vokser med antal processer
	fmt.Println("\n\n### DEMO 5: MESSAGE COMPLEXITY ANALYSIS ###")
	BenchmarkMessageComplexity(50)

	// Demo 6: Ordering Capability Measurement
	// Måler faktisk ordering correctness under forskellige workloads
	fmt.Println("\n\n### DEMO 6: ORDERING CAPABILITY MEASUREMENT ###")
	MeasureOrderingCapability(10, 0.6) // 60% concurrency

	fmt.Println("\n\n=================================================")
	fmt.Println("   SIMULATION COMPLETE")
	fmt.Println("=================================================")
}
