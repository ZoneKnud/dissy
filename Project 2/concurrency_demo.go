package main

import (
	"fmt"
)

// DemonstrateConcurrentMessages viser hvad der sker når to beskeder
// med samme Lamport timestamp ankommer samtidigt
func DemonstrateConcurrentMessages() {
	fmt.Println("\n╔════════════════════════════════════════════════════════════════════╗")
	fmt.Println("║   DEMONSTRATION: CONCURRENT MESSAGE ARRIVAL                        ║")
	fmt.Println("╚════════════════════════════════════════════════════════════════════╝")
	
	fmt.Println()
	fmt.Println("📋 Scenario:")
	fmt.Println("   - 3 processer: P0, P1, P2")
	fmt.Println("   - P1 og P2 sender SAMTIDIGT beskeder til P0")
	fmt.Println("   - Begge sender når deres lokale ur er T=5")
	fmt.Println("   - Kan vi bestemme hvilken besked der 'skete først'?")
	
	// === LAMPORT TEST ===
	fmt.Println()
	fmt.Println("═══════════════════════════════════════════════════════════════════")
	fmt.Println("🔴 TEST MED LAMPORT CLOCK")
	fmt.Println("═══════════════════════════════════════════════════════════════════")
	
	p0_lamport := NewProcess(0, 3, false)
	p1_lamport := NewProcess(1, 3, false)
	p2_lamport := NewProcess(2, 3, false)
	
	// Setup: P1 og P2 laver 5 local events hver
	fmt.Println()
	fmt.Println("Setup: P1 og P2 udfører hver 5 lokale events...")
	for i := 0; i < 5; i++ {
		p1_lamport.LamportClock.LocalEvent()
		p2_lamport.LamportClock.LocalEvent()
	}
	
	fmt.Printf("   P0: T=%d\n", p0_lamport.LamportClock.GetTime())
	fmt.Printf("   P1: T=%d\n", p1_lamport.LamportClock.GetTime())
	fmt.Printf("   P2: T=%d\n", p2_lamport.LamportClock.GetTime())
	
	// Send beskeder
	fmt.Println()
	fmt.Println("📤 P1 og P2 sender SAMTIDIGT beskeder til P0...")
	t1_sent := p1_lamport.LamportClock.SendEvent()
	t2_sent := p2_lamport.LamportClock.SendEvent()
	
	fmt.Printf("   P1 sender M1 med timestamp: T=%d\n", t1_sent)
	fmt.Printf("   P2 sender M2 med timestamp: T=%d\n", t2_sent)
	
	if t1_sent == t2_sent {
		fmt.Println()
		fmt.Println("⚠️  KRITISK: Begge beskeder har SAMME timestamp!")
	}
	
	// Receive
	fmt.Println()
	fmt.Println("📥 P0 modtager begge beskeder...")
	t0_after_m1 := p0_lamport.LamportClock.ReceiveEvent(t1_sent)
	t0_after_m2 := p0_lamport.LamportClock.ReceiveEvent(t2_sent)
	
	fmt.Printf("   P0 efter M1: T=%d\n", t0_after_m1)
	fmt.Printf("   P0 efter M2: T=%d\n", t0_after_m2)
	
	// Analysis
	fmt.Println()
	fmt.Println("🔍 ANALYSE:")
	if t1_sent == t2_sent {
		fmt.Println()
		fmt.Println("❌ LAMPORT LIMITATION:")
		fmt.Printf("   → Begge beskeder har timestamp T=%d\n", t1_sent)
		fmt.Println("   → Lamport kan IKKE fortælle om:")
		fmt.Println("      • M1 skete før M2")
		fmt.Println("      • M2 skete før M1")
		fmt.Println("      • M1 og M2 er concurrent (det rigtige svar!)")
		fmt.Println()
		fmt.Println("   → For at ordne dem må vi bruge en tie-breaker (fx process ID)")
		fmt.Println("   → Men dette er en ARBITRÆR beslutning, ikke baseret på kausalitet")
	}
	
	// === VECTOR TEST ===
	fmt.Println()
	fmt.Println()
	fmt.Println("═══════════════════════════════════════════════════════════════════")
	fmt.Println("🟢 TEST MED VECTOR CLOCK")
	fmt.Println("═══════════════════════════════════════════════════════════════════")
	
	p0_vector := NewProcess(0, 3, true)
	p1_vector := NewProcess(1, 3, true)
	p2_vector := NewProcess(2, 3, true)
	
	// Setup
	fmt.Println()
	fmt.Println("Setup: P1 og P2 udfører hver 5 lokale events...")
	for i := 0; i < 5; i++ {
		p1_vector.VectorClock.LocalEvent()
		p2_vector.VectorClock.LocalEvent()
	}
	
	fmt.Printf("   P0: %s\n", FormatVector(p0_vector.VectorClock.GetVector()))
	fmt.Printf("   P1: %s\n", FormatVector(p1_vector.VectorClock.GetVector()))
	fmt.Printf("   P2: %s\n", FormatVector(p2_vector.VectorClock.GetVector()))
	
	// Send beskeder
	fmt.Println()
	fmt.Println("📤 P1 og P2 sender SAMTIDIGT beskeder til P0...")
	v1_sent := p1_vector.VectorClock.SendEvent()
	v2_sent := p2_vector.VectorClock.SendEvent()
	
	fmt.Printf("   P1 sender M1 med vector: %s\n", FormatVector(v1_sent))
	fmt.Printf("   P2 sender M2 med vector: %s\n", FormatVector(v2_sent))
	
	// Compare
	fmt.Println()
	fmt.Println("🔍 Sammenligning af V(M1) og V(M2):")
	comparison := CompareVectors(v1_sent, v2_sent)
	
	fmt.Printf("   V(M1) = %s\n", FormatVector(v1_sent))
	fmt.Printf("   V(M2) = %s\n", FormatVector(v2_sent))
	fmt.Println()
	
	switch comparison {
	case -1:
		fmt.Println("   Resultat: M1 happened before M2")
	case 1:
		fmt.Println("   Resultat: M2 happened before M1")
	case 0:
		// Check if concurrent or identical
		identical := true
		for i := 0; i < len(v1_sent); i++ {
			if v1_sent[i] != v2_sent[i] {
				identical = false
				break
			}
		}
		
		if !identical {
			fmt.Println("   Resultat: M1 og M2 er CONCURRENT! ✅")
			fmt.Println()
			fmt.Println("   Forklaring:")
			fmt.Printf("      • V(M1)[0]=%d, V(M2)[0]=%d → Begge kender 0 events fra P0\n", v1_sent[0], v2_sent[0])
			fmt.Printf("      • V(M1)[1]=%d, V(M2)[1]=%d → M1 kender P1's events, M2 gør ikke\n", v1_sent[1], v2_sent[1])
			fmt.Printf("      • V(M1)[2]=%d, V(M2)[2]=%d → M2 kender P2's events, M1 gør ikke\n", v1_sent[2], v2_sent[2])
			fmt.Println()
			fmt.Println("   → Ingen af dem vidste om den anden!")
			fmt.Println("   → De er derfor CONCURRENT (uafhængige events)")
		} else {
			fmt.Println("   Resultat: Identiske vectors")
		}
	}
	
	// Receive
	fmt.Println()
	fmt.Println("📥 P0 modtager begge beskeder...")
	v0_before := p0_vector.VectorClock.GetVector()
	fmt.Printf("   P0 før modtagelse:  %s\n", FormatVector(v0_before))
	
	v0_after_m1 := p0_vector.VectorClock.ReceiveEvent(v1_sent)
	fmt.Printf("   P0 efter M1:        %s\n", FormatVector(v0_after_m1))
	
	v0_after_m2 := p0_vector.VectorClock.ReceiveEvent(v2_sent)
	fmt.Printf("   P0 efter M2:        %s\n", FormatVector(v0_after_m2))
	
	// Summary
	fmt.Println()
	fmt.Println()
	fmt.Println("═══════════════════════════════════════════════════════════════════")
	fmt.Println("📊 KONKLUSION")
	fmt.Println("═══════════════════════════════════════════════════════════════════")
	fmt.Println()
	fmt.Println("❌ LAMPORT:")
	fmt.Println("   • Kan IKKE detektere concurrent events")
	fmt.Println("   • Ens timestamps → \"ved ikke\" om rækkefølge")
	fmt.Println("   • Må bruge arbitrær tie-breaker (fx process ID)")
	fmt.Println("   • Risiko for forkert conflict resolution")
	fmt.Println()
	fmt.Println("✅ VECTOR:")
	fmt.Println("   • KAN detektere concurrent events")
	fmt.Println("   • Forskellige vectors → præcis kausal information")
	fmt.Println("   • Kan implementere intelligent conflict resolution")
	fmt.Println("   • Men med O(n) overhead i tid og plads")
	fmt.Println()
	fmt.Println("💡 PRAKTISK BETYDNING:")
	fmt.Println("   → I systemer med concurrent writes (fx replicated databases):")
	fmt.Println("     • Lamport: Risikerer at behandle concurrent writes som ordered")
	fmt.Println("     • Vector:  Kan detektere conflicts og merge korrekt")
	fmt.Println()
	fmt.Println("   → Vælg algoritme baseret på:")
	fmt.Println("     • Behov for concurrency detection")
	fmt.Println("     • Antal processer (Vector's overhead vokser med n)")
	fmt.Println("     • Frequency af concurrent operations")
}
