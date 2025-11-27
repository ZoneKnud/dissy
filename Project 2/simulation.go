package main

import (
	"fmt"
	"strings"
	"time"
)

// Event repræsenterer en hændelse i systemet
type Event struct {
	Type      string // "local", "send", eller "receive"
	ProcessID int    // Hvilken proces der udfører eventet
	TargetID  int    // Hvis Type er "send", hvem sendes beskeden til?
	Message   string // Besked-indhold
}

// Process simulerer en distribueret proces
// Den kan bruge enten Lamport eller Vector clock
type Process struct {
	ID              int
	LamportClock    *LamportClock
	VectorClock     *VectorClock
	EventLog        []string   // Log af alle events
	EventVectors    [][]int    // Gemmer vector clock for hver event (kun hvis UseVectorClock=true)
	EventTimestamps []int      // Gemmer Lamport timestamp for hver event (kun hvis UseVectorClock=false)
	MessageQueue    chan Event // Channel til at modtage beskeder
	UseVectorClock  bool       // Hvis true, brug vector clock, ellers lamport
}

// NewProcess opretter en ny proces
func NewProcess(id int, numProcesses int, useVectorClock bool) *Process {
	return &Process{
		ID:              id,
		LamportClock:    NewLamportClock(),
		VectorClock:     NewVectorClock(numProcesses, id),
		EventLog:        make([]string, 0),
		EventVectors:    make([][]int, 0),      // Pre-allocate for vector snapshots
		EventTimestamps: make([]int, 0),        // Pre-allocate for timestamp snapshots
		MessageQueue:    make(chan Event, 100), // Buffered channel
		UseVectorClock:  useVectorClock,
	}
}

// HandleLocalEvent håndterer en lokal operation
func (p *Process) HandleLocalEvent(message string) {
	if p.UseVectorClock {
		vector := p.VectorClock.LocalEvent()
		p.EventVectors = append(p.EventVectors, copyVector(vector)) // Gem snapshot af vector
		logMsg := fmt.Sprintf("P%d: Local event %s at %s",
			p.ID, FormatVector(vector), message)
		p.EventLog = append(p.EventLog, logMsg)
	} else {
		timestamp := p.LamportClock.LocalEvent()
		p.EventTimestamps = append(p.EventTimestamps, timestamp) // Gem timestamp
		logMsg := fmt.Sprintf("P%d: Local event T%d: %s",
			p.ID, timestamp, message)
		p.EventLog = append(p.EventLog, logMsg)
	}
}

// SendMessage sender en besked til en anden proces
func (p *Process) SendMessage(target *Process, message string) {
	if p.UseVectorClock {
		vector := p.VectorClock.SendEvent()
		p.EventVectors = append(p.EventVectors, copyVector(vector)) // Gem snapshot
		logMsg := fmt.Sprintf("P%d: Send to P%d at %s: %s",
			p.ID, target.ID, FormatVector(vector), message)
		p.EventLog = append(p.EventLog, logMsg)

		// Send beskeden til target's queue
		target.MessageQueue <- Event{
			Type:      "receive",
			ProcessID: p.ID,
			Message:   fmt.Sprintf("%s|%s", FormatVector(vector), message),
		}
	} else {
		timestamp := p.LamportClock.SendEvent()
		p.EventTimestamps = append(p.EventTimestamps, timestamp) // Gem timestamp
		logMsg := fmt.Sprintf("P%d: Send to P%d at T%d: %s",
			p.ID, target.ID, timestamp, message)
		p.EventLog = append(p.EventLog, logMsg)

		// Send beskeden til target's queue
		target.MessageQueue <- Event{
			Type:      "receive",
			ProcessID: p.ID,
			Message:   fmt.Sprintf("%d|%s", timestamp, message),
		}
	}
}

// ReceiveMessage håndterer modtagelse af en besked
func (p *Process) ReceiveMessage(event Event) {
	// Parse timestamp fra beskeden
	var logMsg string

	if p.UseVectorClock {
		// Parse vector fra beskeden
		// Beskeden indeholder vectoren i event.Message
		// Vi skal bruge den faktiske receivedVector fra SendMessage

		// For nu parser vi den fra beskeden
		// I en rigtig implementation ville man måske bruge JSON
		var receivedVector []int

		// Extract vector from message (format: "[1,2,3]|content")
		parts := splitMessage(event.Message)
		if len(parts) == 2 {
			receivedVector = parseVector(parts[0])
		} else {
			// Fallback: brug en tom vector
			receivedVector = make([]int, len(p.VectorClock.vector))
		}

		// Gem vores vector før receive (for at vise synkronisering)
		beforeVector := p.VectorClock.GetVector()

		vector := p.VectorClock.ReceiveEvent(receivedVector)
		p.EventVectors = append(p.EventVectors, copyVector(vector)) // Gem snapshot efter receive

		// Vis synkroniseringen tydeligt
		logMsg = fmt.Sprintf("P%d: Receive from P%d (received %s, was %s → synchronized to %s): %s",
			p.ID, event.ProcessID, FormatVector(receivedVector),
			FormatVector(beforeVector), FormatVector(vector), parts[1])
	} else {
		// Parse lamport timestamp fra beskeden
		// Beskeden indeholder timestamp i format: "T|content"
		parts := splitMessage(event.Message)
		receivedTime := 0
		if len(parts) == 2 {
			fmt.Sscanf(parts[0], "%d", &receivedTime)
		}

		// Gem vores tid før receive (for at vise synkronisering)
		beforeTime := p.LamportClock.GetTime()

		timestamp := p.LamportClock.ReceiveEvent(receivedTime)
		p.EventTimestamps = append(p.EventTimestamps, timestamp) // Gem timestamp efter receive

		// Vis synkroniseringen tydeligt
		logMsg = fmt.Sprintf("P%d: Receive from P%d (received T%d, was T%d → synchronized to T%d): %s",
			p.ID, event.ProcessID, receivedTime, beforeTime, timestamp, parts[1])
	}

	p.EventLog = append(p.EventLog, logMsg)
}

// splitMessage splitter en besked ved '|' separatoren
func splitMessage(message string) []string {
	for i, ch := range message {
		if ch == '|' {
			return []string{message[:i], message[i+1:]}
		}
	}
	return []string{message}
}

// parseVector parser en vector string "[1,2,3]" til []int
func parseVector(vectorStr string) []int {
	// Fjern [ og ]
	vectorStr = vectorStr[1 : len(vectorStr)-1]

	// Split ved komma
	parts := make([]string, 0)
	current := ""
	for _, ch := range vectorStr {
		if ch == ',' {
			parts = append(parts, current)
			current = ""
		} else {
			current += string(ch)
		}
	}
	if current != "" {
		parts = append(parts, current)
	}

	// Convert til ints
	result := make([]int, len(parts))
	for i, part := range parts {
		fmt.Sscanf(part, "%d", &result[i])
	}

	return result
}

// Run starter processen og lytter efter beskeder
func (p *Process) Run(done chan bool) {
	go func() {
		for {
			select {
			case event := <-p.MessageQueue:
				p.ReceiveMessage(event)
			case <-done:
				return
			case <-time.After(100 * time.Millisecond):
				// Timeout for at undgå at hænge
				continue
			}
		}
	}()
}

// Simulation håndterer hele den distribuerede system simulation
type Simulation struct {
	Processes      []*Process
	UseVectorClock bool
}

// NewSimulation opretter en ny simulation
func NewSimulation(numProcesses int, useVectorClock bool) *Simulation {
	processes := make([]*Process, numProcesses)
	for i := 0; i < numProcesses; i++ {
		processes[i] = NewProcess(i, numProcesses, useVectorClock)
	}

	return &Simulation{
		Processes:      processes,
		UseVectorClock: useVectorClock,
	}
}

// RunScenario kører et forudbestemt scenario af events
func (sim *Simulation) RunScenario() {
	// Start alle processer
	done := make(chan bool)
	for _, p := range sim.Processes {
		p.Run(done)
	}

	// Vent lidt så alt er klar
	time.Sleep(50 * time.Millisecond)

	// Scenario: En række events der viser causal relationships
	fmt.Println("\n=== Running Scenario ===")

	// Alle processer starter med local events (realistisk!)
	// Dette simulerer at hver proces har sit eget arbejde
	fmt.Println("Phase 1: Initial local events (processer arbejder uafhængigt)")
	sim.Processes[0].HandleLocalEvent("Initialize P0")
	sim.Processes[1].HandleLocalEvent("Initialize P1")
	sim.Processes[2].HandleLocalEvent("Initialize P2")
	time.Sleep(10 * time.Millisecond)

	// Flere initial events for at gøre det mere realistisk
	sim.Processes[1].HandleLocalEvent("P1 local work")
	sim.Processes[2].HandleLocalEvent("P2 local work")
	time.Sleep(10 * time.Millisecond)

	// Nu begynder kommunikationen
	fmt.Println("Phase 2: Communication starts")

	// P0 har et lokalt event
	sim.Processes[0].HandleLocalEvent("Event A")
	time.Sleep(10 * time.Millisecond)

	// P0 sender til P1
	sim.Processes[0].SendMessage(sim.Processes[1], "Message from P0")
	time.Sleep(20 * time.Millisecond)

	// P1 har et lokalt event EFTER at have modtaget
	sim.Processes[1].HandleLocalEvent("Event B")
	time.Sleep(10 * time.Millisecond)

	// P1 sender til P2
	sim.Processes[1].SendMessage(sim.Processes[2], "Message from P1")
	time.Sleep(20 * time.Millisecond)

	// P2 har et lokalt event EFTER at have modtaget
	sim.Processes[2].HandleLocalEvent("Event C")
	time.Sleep(10 * time.Millisecond)

	// P2 sender til P0 (skaber en cycle)
	sim.Processes[2].SendMessage(sim.Processes[0], "Message from P2")
	time.Sleep(30 * time.Millisecond)

	// P0 og P2 har concurrent local events
	go sim.Processes[0].HandleLocalEvent("Event D")
	go sim.Processes[2].HandleLocalEvent("Event E")
	time.Sleep(20 * time.Millisecond)

	// Stop alle processer
	close(done)
	time.Sleep(50 * time.Millisecond)

	// Print event logs
	sim.PrintLogs()
}

// PrintLogs printer event logs fra alle processer
func (sim *Simulation) PrintLogs() {
	fmt.Println("\n=== Event Logs ===")
	for _, p := range sim.Processes {
		fmt.Printf("\nProcess %d:\n", p.ID)
		for _, log := range p.EventLog {
			fmt.Println("  " + log)
		}
	}
}

// GetClockType returnerer en string der beskriver hvilken clock der bruges
func (sim *Simulation) GetClockType() string {
	if sim.UseVectorClock {
		return "Vector Clock"
	}
	return "Lamport Clock"
}

// RunConcurrentScenario demonstrerer concurrent message arrival
// P1 og P2 sender beskeder til P0 samtidigt
func (sim *Simulation) RunConcurrentScenario() {
	// Start alle processer
	done := make(chan bool)
	for _, p := range sim.Processes {
		p.Run(done)
	}
	time.Sleep(10 * time.Millisecond)

	// P1 og P2 laver lokale events først
	for i := 0; i < 5; i++ {
		sim.Processes[1].HandleLocalEvent(fmt.Sprintf("Work-%d", i+1))
		sim.Processes[2].HandleLocalEvent(fmt.Sprintf("Work-%d", i+1))
	}

	// Send beskeder samtidigt til P0
	sim.Processes[1].SendMessage(sim.Processes[0], "Data from P1")
	sim.Processes[2].SendMessage(sim.Processes[0], "Data from P2")

	// Vent på at beskeder modtages
	time.Sleep(50 * time.Millisecond)

	// Stop processer
	close(done)
	time.Sleep(20 * time.Millisecond)
}

// PrintRecentLogs printer de sidste n events fra hver proces
func (sim *Simulation) PrintRecentLogs(n int) {
	fmt.Println("\n=== Event Logs (Recent) ===")
	for _, p := range sim.Processes {
		fmt.Printf("\nProcess %d:\n", p.ID)

		// Find start index for de sidste n events
		startIdx := 0
		if len(p.EventLog) > n {
			startIdx = len(p.EventLog) - n
		}

		for i := startIdx; i < len(p.EventLog); i++ {
			fmt.Println("  " + p.EventLog[i])
		}
	}
}

// DemonstrateConcurrentMessages viser hvordan Lamport og Vector clocks håndterer
// concurrent message arrival - en kritisk situation hvor to beskeder sendes samtidigt
func DemonstrateConcurrentMessages() {
	fmt.Println("\nScenario:")
	fmt.Println("  • 3 processer: P0, P1, P2")
	fmt.Println("  • P1 og P2 udfører hver 5 local events")
	fmt.Println("  • Derefter sender både P1 og P2 en besked til P0 SAMTIDIGT")
	fmt.Println("  • Vi observerer hvordan hver clock type håndterer dette")

	// Lamport Clock
	fmt.Println("\n" + strings.Repeat("═", 64))
	fmt.Println("Part 1: Lamport Clock")
	fmt.Println(strings.Repeat("═", 64))

	lamportSim := NewSimulation(3, false)

	fmt.Println("\nPhase 1: Setup - P1 and P2 perform local events")
	fmt.Println("Phase 2: Concurrent message sending")
	fmt.Println("P1 og P2 sender SAMTIDIGT beskeder til P0")

	lamportSim.RunConcurrentScenario()
	lamportSim.PrintRecentLogs(3)

	fmt.Println("\n=== Analysis ===")
	fmt.Println("Observation: Begge beskeder sendes med timestamp T=6")
	fmt.Println("Problem: Lamport clock kan ikke skelne mellem:")
	fmt.Println("  1. M1 happened-before M2")
	fmt.Println("  2. M2 happened-before M1")
	fmt.Println("  3. M1 and M2 are concurrent (korrekt svar)")
	fmt.Println("Konsekvens: Må bruge tie-breaker (fx process ID) for ordering")

	// Vector Clock
	fmt.Println("\n" + strings.Repeat("═", 64))
	fmt.Println("Part 2: Vector Clock")
	fmt.Println(strings.Repeat("═", 64))

	vectorSim := NewSimulation(3, true)

	fmt.Println("\nPhase 1: Setup - P1 and P2 perform local events")
	fmt.Println("Phase 2: Concurrent message sending")
	fmt.Println("P1 og P2 sender SAMTIDIGT beskeder til P0")

	vectorSim.RunConcurrentScenario()
	vectorSim.PrintRecentLogs(3)

	fmt.Println("\n=== Analysis ===")
	fmt.Println("Observation: Vector clocks viser:")
	fmt.Println("  • P1's besked: [0,6,0] - kun P1 har kørt events")
	fmt.Println("  • P2's besked: [0,0,6] - kun P2 har kørt events")
	fmt.Println("Konklusion: Ingen af vektorene dominerer den anden")
	fmt.Println("Resultat: Vector clock detekterer korrekt at beskederne er CONCURRENT")

	fmt.Println("\n" + strings.Repeat("═", 64))
	fmt.Println("Key Takeaway:")
	fmt.Println("  Lamport: Kan ikke detektere concurrency → kræver tie-breaker")
	fmt.Println("  Vector:  Detekterer concurrency præcist → ordner kun ved causality")
	fmt.Println(strings.Repeat("═", 64))
}

// copyVector laver en dyb kopi af en vector
// Dette er nødvendigt for at gemme snapshots af vector clocks
func copyVector(v []int) []int {
	if v == nil {
		return nil
	}
	copy := make([]int, len(v))
	for i := range v {
		copy[i] = v[i]
	}
	return copy
}
