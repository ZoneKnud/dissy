package main

import (
	"fmt"
)

// DemonstrateConcurrentMessageArrival demonstrerer Lamport's limitation:
// Når to beskeder ankommer samtidigt med samme timestamp, kan vi ikke bestemme rækkefølgen
func DemonstrateConcurrentMessageArrival() {
	fmt.Println("\n\n╔════════════════════════════════════════════════════════════════════╗")
	fmt.Println("║   TEST: CONCURRENT MESSAGE ARRIVAL - LAMPORT'S LIMITATION         ║")
	fmt.Println("╚════════════════════════════════════════════════════════════════════╝")
	
	fmt.Println()
	fmt.Println("📋 Scenario:")
	fmt.Println("   - Process P0, P1, P2 eksisterer")
	fmt.Println("   - P1 og P2 sender SAMTIDIGT beskeder til P0")
	fmt.Println("   - Begge beskeder har timestamp T=5")
	fmt.Println("   - Vi tester om systemet kan bestemme hvilken besked der 'skete først'")
	
	// Test med Lamport
	fmt.Println()
	fmt.Println("═══════════════════════════════════════════════════════════════════")
	fmt.Println("🔴 TEST 1: LAMPORT CLOCK")
	fmt.Println("═══════════════════════════════════════════════════════════════════")
	fmt.Println()
	
	testLamportConcurrency()
	
	// Test med Vector
	fmt.Println()
	fmt.Println("═══════════════════════════════════════════════════════════════════")
	fmt.Println("🟢 TEST 2: VECTOR CLOCK")
	fmt.Println("═══════════════════════════════════════════════════════════════════")
	fmt.Println()
	
	testVectorConcurrency()
	
	// Konklusion
	fmt.Println("\n═══════════════════════════════════════════════════════════════════")
	fmt.Println("📊 KONKLUSION")
	fmt.Println("═══════════════════════════════════════════════════════════════════")
	fmt.Println("❌ LAMPORT: Kan IKKE bestemme om beskederne er concurrent eller ej")
	fmt.Println("   → Begge har samme timestamp T=6 efter receive")
	fmt.Println("   → Kan ikke sige om M1 skete før M2 eller omvendt")
	fmt.Println("   → Kan ikke detektere at de er concurrent")
	fmt.Println()
	
	fmt.Println("✅ VECTOR: Kan PRÆCIST bestemme at beskederne er concurrent")
	fmt.Println("   → V(M1) = [0,5,0] og V(M2) = [0,0,5]")
	fmt.Println("   → CompareVectors viser: CONCURRENT (ingen happens-before)")
	fmt.Println("   → Systemet VED at de skete uafhængigt af hinanden")
	fmt.Println()
	
	fmt.Println("💡 PRAKTISK BETYDNING:")
	fmt.Println("   I et konflikt-resolution system:")
	fmt.Println("   - Lamport: Må bruge tie-breaker (fx process ID) → arbitrær")
	fmt.Println("   - Vector:  Kan detektere konflikt og merge intelligent")
	fmt.Println()
}

func testLamportConcurrency() {
	// Opret 3 processer
	p0 := NewProcess(0, 3, false)
	p1 := NewProcess(1, 3, false)
	p2 := NewProcess(2, 3, false)
	
	fmt.Println("📍 Initial state:")
	fmt.Printf("   P0: T=%d\n", p0.LamportClock.GetTime())
	fmt.Printf("   P1: T=%d\n", p1.LamportClock.GetTime())
	fmt.Printf("   P2: T=%d\n", p2.LamportClock.GetTime())
	
	// Begge processer laver samme antal local events for at synkronisere timestamps
	fmt.Println("\n🔄 Setup: P1 og P2 laver hver 5 local events...")
	for i := 0; i < 5; i++ {
		p1.LamportClock.LocalEvent()
		p2.LamportClock.LocalEvent()
	}
	
	fmt.Printf("   P1: T=%d\n", p1.LamportClock.GetTime())
	fmt.Printf("   P2: T=%d\n", p2.LamportClock.GetTime())
	
	// Nu sender BEGGE beskeder til P0 på samme tid
	fmt.Println("\n📤 KRITISK PUNKT: P1 og P2 sender SAMTIDIGT til P0...")
	
	// Send events (increment timestamp)
	t1_sent := p1.LamportClock.SendEvent()
	t2_sent := p2.LamportClock.SendEvent()
	
	fmt.Printf("   P1 sender besked M1 med timestamp: T=%d\n", t1_sent)
	fmt.Printf("   P2 sender besked M2 med timestamp: T=%d\n", t2_sent)
	
	if t1_sent == t2_sent {
		fmt.Println("\n⚠️  PROBLEM: Begge beskeder har SAMME timestamp!")
	}
	
	// P0 modtager begge beskeder
	fmt.Println("\n📥 P0 modtager begge beskeder...")
	
	// Simuler at de ankommer samtidigt ved at modtage dem uden delay
	t0_after_m1 := p0.LamportClock.ReceiveEvent(t1_sent)
	t0_after_m2 := p0.LamportClock.ReceiveEvent(t2_sent)
	
	fmt.Printf("   P0 efter receive M1: T=%d\n", t0_after_m1)
	fmt.Printf("   P0 efter receive M2: T=%d\n", t0_after_m2)
	
	// Analyse
	fmt.Println("\n🔍 ANALYSE:")
	fmt.Printf("   M1 sendt med T=%d, M2 sendt med T=%d\n", t1_sent, t2_sent)
	fmt.Printf("   P0 efter M1: T=%d, efter M2: T=%d\n", t0_after_m1, t0_after_m2)
	
	if t1_sent == t2_sent {
		fmt.Println("\n❌ LIMITATION DEMONSTRERET:")
		fmt.Printf("   → Begge beskeder HAR samme timestamp (T=%d)\n", t1_sent)
		fmt.Println("   → Lamport kan IKKE fortælle om:")
		fmt.Println("      • M1 skete før M2")
		fmt.Println("      • M2 skete før M1")
		fmt.Println("      • M1 og M2 er concurrent (det rigtige svar!)")
		fmt.Println("\n   → Hvis vi sammenligner T1 og T2:")
		fmt.Printf("      T1 (%d) == T2 (%d) → KAN IKKE BESTEMME RÆKKEFØLGE\n", t1_sent, t2_sent)
		fmt.Println("\n   → Dette er en FUNDAMENTAL LIMITATION af Lamport!")
	}
}

func testVectorConcurrency() {
	// Opret 3 processer med vector clocks
	p0 := NewProcess(0, 3, true)
	p1 := NewProcess(1, 3, true)
	p2 := NewProcess(2, 3, true)
	
	fmt.Println("📍 Initial state:")
	fmt.Printf("   P0: %s\n", FormatVector(p0.VectorClock.GetVector()))
	fmt.Printf("   P1: %s\n", FormatVector(p1.VectorClock.GetVector()))
	fmt.Printf("   P2: %s\n", FormatVector(p2.VectorClock.GetVector()))
	
	// Begge processer laver samme antal local events
	fmt.Println("\n🔄 Setup: P1 og P2 laver hver 5 local events...")
	for i := 0; i < 5; i++ {
		p1.VectorClock.LocalEvent()
		p2.VectorClock.LocalEvent()
	}
	
	fmt.Printf("   P1: %s\n", FormatVector(p1.VectorClock.GetVector()))
	fmt.Printf("   P2: %s\n", FormatVector(p2.VectorClock.GetVector()))
	
	// Nu sender BEGGE beskeder til P0 på samme tid
	fmt.Println("\n📤 KRITISK PUNKT: P1 og P2 sender SAMTIDIGT til P0...")
	
	// Send events
	v1_sent := p1.VectorClock.SendEvent()
	v2_sent := p2.VectorClock.SendEvent()
	
	fmt.Printf("   P1 sender besked M1 med vector: %s\n", FormatVector(v1_sent))
	fmt.Printf("   P2 sender besked M2 med vector: %s\n", FormatVector(v2_sent))
	
	// Sammenlign vectors
	comparison := CompareVectors(v1_sent, v2_sent)
	fmt.Println("\n🔍 Sammenligning af V(M1) og V(M2):")
	fmt.Printf("   V(M1) = %s\n", FormatVector(v1_sent))
	fmt.Printf("   V(M2) = %s\n", FormatVector(v2_sent))
	
	switch comparison {
	case -1:
		fmt.Println("   Result: V(M1) < V(M2) → M1 happened before M2")
	case 1:
		fmt.Println("   Result: V(M1) > V(M2) → M2 happened before M1")
	case 0:
		// Check if actually concurrent or identical
		identical := true
		for i := 0; i < len(v1_sent); i++ {
			if v1_sent[i] != v2_sent[i] {
				identical = false
				break
			}
		}
		
		if identical {
			fmt.Println("   Result: V(M1) == V(M2) → Samme event")
		} else {
			fmt.Println("   Result: V(M1) || V(M2) → M1 og M2 er CONCURRENT!")
			fmt.Println("\n✅ PERFEKT! Vector clock DETEKTERER concurrency:")
			fmt.Printf("      • V(M1)[0]=%d, V(M2)[0]=%d → P0's position: equal\n", v1_sent[0], v2_sent[0])
			fmt.Printf("      • V(M1)[1]=%d, V(M2)[1]=%d → P1's position: M1 vidste mere\n", v1_sent[1], v2_sent[1])
			fmt.Printf("      • V(M1)[2]=%d, V(M2)[2]=%d → P2's position: M2 vidste mere\n", v1_sent[2], v2_sent[2])
			fmt.Println("      → Ingen af dem vidste om den anden!")
			fmt.Println("      → Derfor er de CONCURRENT (uafhængige events)")
		}
	}
	
	// P0 modtager begge beskeder
	fmt.Println("\n📥 P0 modtager begge beskeder...")
	
	v0_before := p0.VectorClock.GetVector()
	fmt.Printf("   P0 før modtagelse: %s\n", FormatVector(v0_before))
	
	v0_after_m1 := p0.VectorClock.ReceiveEvent(v1_sent)
	fmt.Printf("   P0 efter M1:       %s\n", FormatVector(v0_after_m1))
	
	v0_after_m2 := p0.VectorClock.ReceiveEvent(v2_sent)
	fmt.Printf("   P0 efter M2:       %s\n", FormatVector(v0_after_m2))
	
	fmt.Println("\n✅ FORDEL: P0 ved nu besked om ALLE events der skete:")
	fmt.Printf("   • P0 har lavet %d events\n", v0_after_m2[0])
	fmt.Printf("   • P1 har lavet %d events (vidste P0 om via M1)\n", v0_after_m2[1])
	fmt.Printf("   • P2 har lavet %d events (vidste P0 om via M2)\n", v0_after_m2[2])
}

// TestLamportTieBreaker viser hvordan man typisk håndterer Lamport's limitation
func DemonstrateLamportTieBreaker() {
	fmt.Println("\n\n╔════════════════════════════════════════════════════════════════════╗")
	fmt.Println("║   TEST: LAMPORT TIE-BREAKER STRATEGY                              ║")
	fmt.Println("╚════════════════════════════════════════════════════════════════════╝")
	
	fmt.Println()
	fmt.Println("📋 Problem: Hvad gør vi når Lamport timestamps er ens?")
	fmt.Println("   → Standard løsning: Brug process ID som tie-breaker")
	fmt.Println()
	
	// Simuler to events med samme timestamp
	type TimestampedEvent struct {
		ProcessID int
		Timestamp int
		Content   string
	}
	
	event1 := TimestampedEvent{ProcessID: 1, Timestamp: 5, Content: "Write X=10"}
	event2 := TimestampedEvent{ProcessID: 2, Timestamp: 5, Content: "Write X=20"}
	
	fmt.Println("📍 To events med samme timestamp:")
	fmt.Printf("   Event 1: P%d T=%d: %s\n", event1.ProcessID, event1.Timestamp, event1.Content)
	fmt.Printf("   Event 2: P%d T=%d: %s\n", event2.ProcessID, event2.Timestamp, event2.Content)
	
	// Compare function
	compare := func(e1, e2 TimestampedEvent) int {
		if e1.Timestamp < e2.Timestamp {
			return -1
		} else if e1.Timestamp > e2.Timestamp {
			return 1
		} else {
			// Timestamp er ens - brug process ID som tie-breaker
			if e1.ProcessID < e2.ProcessID {
				return -1
			} else if e1.ProcessID > e2.ProcessID {
				return 1
			}
			return 0
		}
	}
	
	result := compare(event1, event2)
	
	fmt.Println("\n🔍 Sammenligning med tie-breaker:")
	fmt.Printf("   compare(E1, E2) = %d\n", result)
	
	if result < 0 {
		fmt.Printf("   → Event 1 (P%d) kommer før Event 2 (P%d)\n", event1.ProcessID, event2.ProcessID)
	} else {
		fmt.Printf("   → Event 2 (P%d) kommer før Event 1 (P%d)\n", event2.ProcessID, event1.ProcessID)
	}
	
	fmt.Println("\n⚠️  VIGTIGT:")
	fmt.Println("   ❌ Dette er en ARBITRÆR beslutning!")
	fmt.Println("   ❌ Event 1 skete IKKE nødvendigvis før Event 2")
	fmt.Println("   ❌ De kan faktisk være CONCURRENT")
	fmt.Println("   ✅ Men vi er NØDT til at vælge en rækkefølge")
	fmt.Println("   ✅ Process ID tie-breaker giver deterministisk ordering")
	
	fmt.Println("\n💡 Anvendelse:")
	fmt.Println("   → Bruges i systemer der SKAL have total ordering")
	fmt.Println("   → Men hvor concurrency detection ikke er kritisk")
	fmt.Println("   → F.eks: Log aggregation, event sourcing (uden conflicts)")
}

// TestRaceConditionExample viser et konkret race condition eksempel
func DemonstrateRaceConditionExample() {
	fmt.Println("\n\n╔════════════════════════════════════════════════════════════════════╗")
	fmt.Println("║   TEST: REAL-WORLD RACE CONDITION SCENARIO                        ║")
	fmt.Println("╚════════════════════════════════════════════════════════════════════╝")
	
	fmt.Println()
	fmt.Println("📋 Scenario: Distribueret bankkonto")
	fmt.Println("   → Initial balance: 100 kr")
	fmt.Println("   → Transaction 1 (P1): Withdraw 50 kr")
	fmt.Println("   → Transaction 2 (P2): Withdraw 60 kr")
	fmt.Println("   → Begge transaktioner sker SAMTIDIGT")
	fmt.Println()
	
	// Simuler med Lamport
	fmt.Println("═══════════════════════════════════════════════════════════════════")
	fmt.Println("🔴 MED LAMPORT CLOCK:")
	fmt.Println("═══════════════════════════════════════════════════════════════════")
	
	balance := 100
	
	// Simuler at begge transaktioner har samme timestamp
	t1 := 5
	t2 := 5
	
	fmt.Printf("\n   T1 (P1): Withdraw 50 kr @ T=%d\n", t1)
	fmt.Printf("   T2 (P2): Withdraw 60 kr @ T=%d\n", t2)
	fmt.Println("\n   Timestamps er ens! Hvilket skal udføres først?")
	
	// Tie-breaker: process ID
	fmt.Println("\n   → Bruger process ID tie-breaker: P1 < P2")
	fmt.Println("   → Udfører T1 først, derefter T2")
	
	balance -= 50 // T1
	fmt.Printf("   Efter T1: Balance = %d kr\n", balance)
	
	if balance >= 60 {
		balance -= 60 // T2
		fmt.Printf("   Efter T2: Balance = %d kr\n", balance)
	} else {
		fmt.Printf("   ❌ T2 REJECTED: Insufficient funds (need 60, have %d)\n", balance)
	}
	
	fmt.Println("\n   ⚠️  Men hvad hvis de FAKTISK var concurrent?")
	fmt.Println("   → Begge læste initial balance = 100 kr")
	fmt.Println("   → Begge mente de havde nok penge")
	fmt.Println("   → En af dem får fejl pga. arbitrær ordering")
	
	// Simuler med Vector
	fmt.Println("\n═══════════════════════════════════════════════════════════════════")
	fmt.Println("🟢 MED VECTOR CLOCK:")
	fmt.Println("═══════════════════════════════════════════════════════════════════")
	
	balance = 100
	
	v1 := []int{0, 5, 0}
	v2 := []int{0, 0, 5}
	
	fmt.Printf("\n   T1 (P1): Withdraw 50 kr @ V=%s\n", FormatVector(v1))
	fmt.Printf("   T2 (P2): Withdraw 60 kr @ V=%s\n", FormatVector(v2))
	
	comparison := CompareVectors(v1, v2)
	
	if comparison == 0 && v1[0] == v2[0] && v1[1] != v2[1] {
		fmt.Println("\n   ✅ DETECTED: Vectors er CONCURRENT!")
		fmt.Println("   → System ved at der er en CONFLICT")
		fmt.Println("   → Kan trigger konflikt-resolution:")
		fmt.Println("\n   Option 1: Reject begge, kræv user resolution")
		fmt.Println("   Option 2: Merge semantics (sum = 110 kr withdrawal)")
		fmt.Println("   Option 3: Last-write-wins (med warning)")
		fmt.Println("\n   → User kan se at DER VAR et problem")
		fmt.Println("   → Ikke bare en arbitrær rejection")
	}
}

// RunConcurrencyTests kører alle concurrency tests
func RunConcurrencyTests() {
	DemonstrateConcurrentMessageArrival()
	DemonstrateLamportTieBreaker()
	DemonstrateRaceConditionExample()
	
	fmt.Println("\n\n╔════════════════════════════════════════════════════════════════════╗")
	fmt.Println("║   SUMMARY: CONCURRENCY TESTING COMPLETE                           ║")
	fmt.Println("╚════════════════════════════════════════════════════════════════════╝")
	
	fmt.Println("\n📊 Key Findings:")
	fmt.Println("\n1️⃣  LAMPORT LIMITATION:")
	fmt.Println("   → Kan IKKE detektere concurrent events")
	fmt.Println("   → Ens timestamps betyder 'ved ikke'")
	fmt.Println("   → Nødt til at bruge tie-breaker (arbitrær)")
	
	fmt.Println("\n2️⃣  VECTOR ADVANTAGE:")
	fmt.Println("   → KAN detektere concurrent events")
	fmt.Println("   → Giver mulighed for intelligent conflict resolution")
	fmt.Println("   → Men med O(n) overhead cost")
	
	fmt.Println("\n3️⃣  PRACTICAL IMPACT:")
	fmt.Println("   → Conflict-critical systems: SKAL bruge Vector (eller DVV)")
	fmt.Println("   → Append-only systems: Lamport er tilstrækkeligt")
	fmt.Println("   → Choice depends on application semantics")
	
	fmt.Println("\n💡 Recommendation:")
	fmt.Println("   → Hvis concurrent writes kan ske: Brug Vector")
	fmt.Println("   → Hvis conflicts er sjældne/acceptable: Brug Lamport")
	fmt.Println("   → Hvis scale > 100 processer + conflicts: Brug DVV eller CRDT")
}
