package main

import (
	"fmt"
	"strings"
	"sync"
)

// VectorClock struct
type VectorClock struct {
	vector    []int
	processID int
	mutex     sync.Mutex
}

// Opretter et nyt Vector clock
func NewVectorClock(numProcesses int, processID int) *VectorClock {
	vector := make([]int, numProcesses) // Lav et array med 0'er
	return &VectorClock{
		vector:    vector,
		processID: processID,
	}
}

// Processen udfører en lokal operation
func (vc *VectorClock) LocalEvent() []int {
	vc.mutex.Lock()
	defer vc.mutex.Unlock()

	vc.vector[vc.processID]++
	return vc.getCopy()
}

// Send event, increment proces counter og returnerer hele vectoren
func (vc *VectorClock) SendEvent() []int {
	vc.mutex.Lock()
	defer vc.mutex.Unlock()

	vc.vector[vc.processID]++
	return vc.getCopy()
}

// Merge proces' vector med recieved vector
func (vc *VectorClock) ReceiveEvent(receivedVector []int) []int {
	vc.mutex.Lock()
	defer vc.mutex.Unlock()

	// Merge: tag maximum af hver position
	for i := 0; i < len(vc.vector); i++ {
		if receivedVector[i] > vc.vector[i] {
			vc.vector[i] = receivedVector[i]
		}
	}

	vc.vector[vc.processID]++
	return vc.getCopy()
}

// Returnerer en kopi
func (vc *VectorClock) getCopy() []int {
	copy := make([]int, len(vc.vector))
	for i := 0; i < len(vc.vector); i++ {
		copy[i] = vc.vector[i]
	}
	return copy
}

// Retuner aktuel vector
func (vc *VectorClock) GetVector() []int {
	vc.mutex.Lock()
	defer vc.mutex.Unlock()
	return vc.getCopy()
}

// Sammenlign vectors og find relation
func CompareVectors(v1, v2 []int) int {
	if len(v1) != len(v2) {
		panic("Vector clocks skal have samme længde!")
	}

	lessOrEqual := true    // Er v1 <= v2?
	greaterOrEqual := true // Er v1 >= v2?

	for i := 0; i < len(v1); i++ {
		if v1[i] > v2[i] {
			lessOrEqual = false
		}
		if v1[i] < v2[i] {
			greaterOrEqual = false
		}
	}

	// Hvis v1 <= v2 og mindst ét element er mindre
	if lessOrEqual && !greaterOrEqual {
		return -1 // v1 happened before v2
	}

	// Hvis v1 >= v2 og mindst ét element er større
	if greaterOrEqual && !lessOrEqual {
		return 1 // v2 happened before v1
	}

	// Hvis v1 == v2
	if lessOrEqual && greaterOrEqual {
		return 0 // De er identiske (samme event eller concurrent)
	}

	return 0
}

// Vector besked med timestamp
type VectorMessage struct {
	Timestamp []int  // Vector clock når beskeden blev sendt
	ProcessID int    // ID på den proces der sendte beskeden
	Content   string // Besked-indhold
}

// Print funktion
func (msg VectorMessage) String() string {
	// Konverter vector til string format: [1,2,3]
	vectorStr := "["
	for i, v := range msg.Timestamp {
		if i > 0 {
			vectorStr += ","
		}
		vectorStr += fmt.Sprintf("%d", v)
	}
	vectorStr += "]"

	return fmt.Sprintf("P%d@%s: %s", msg.ProcessID, vectorStr, msg.Content)
}

// Print funktion 
func FormatVector(v []int) string {
	parts := make([]string, len(v))
	for i, val := range v {
		parts[i] = fmt.Sprintf("%d", val)
	}
	return "[" + strings.Join(parts, ",") + "]"
}
