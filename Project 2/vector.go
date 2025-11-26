package main

import (
	"fmt"
	"strings"
	"sync"
)

// VectorClock er en mere avanceret logisk ur implementation
// Den holder et array af counters - én for hver proces i systemet
// Dette gør det muligt at opnå total ordering af events
type VectorClock struct {
	vector    []int      // Et array hvor index er processID og værdi er dens tid
	processID int        // Denne proces' ID
	mutex     sync.Mutex // Sikrer thread-safety
}

// NewVectorClock opretter et nyt Vector clock
// numProcesses: hvor mange processer der er i systemet
// processID: ID for denne specifikke proces (0-indexed)
func NewVectorClock(numProcesses int, processID int) *VectorClock {
	vector := make([]int, numProcesses) // Lav et array med 0'er
	return &VectorClock{
		vector:    vector,
		processID: processID,
	}
}

// LocalEvent kaldes når processen udfører en lokal operation
// Den øger kun denne proces' egen counter i vectoren
func (vc *VectorClock) LocalEvent() []int {
	vc.mutex.Lock()
	defer vc.mutex.Unlock()
	
	vc.vector[vc.processID]++
	return vc.getCopy()
}

// SendEvent kaldes før en besked sendes
// Den øger denne proces' counter og returnerer hele vectoren
func (vc *VectorClock) SendEvent() []int {
	vc.mutex.Lock()
	defer vc.mutex.Unlock()
	
	vc.vector[vc.processID]++
	return vc.getCopy()
}

// ReceiveEvent kaldes når en besked modtages
// Den merger denne vector med den modtagne vector:
// For hver position i vectoren, tag max(vores værdi, deres værdi)
// Dette sikrer at vi ved besked om alle events der skete før denne besked
func (vc *VectorClock) ReceiveEvent(receivedVector []int) []int {
	vc.mutex.Lock()
	defer vc.mutex.Unlock()
	
	// Merge: tag maximum af hver position
	for i := 0; i < len(vc.vector); i++ {
		if receivedVector[i] > vc.vector[i] {
			vc.vector[i] = receivedVector[i]
		}
	}
	
	// Øg vores egen counter
	vc.vector[vc.processID]++
	return vc.getCopy()
}

// getCopy returnerer en kopi af vectoren (skal allerede være locked)
func (vc *VectorClock) getCopy() []int {
	copy := make([]int, len(vc.vector))
	for i := 0; i < len(vc.vector); i++ {
		copy[i] = vc.vector[i]
	}
	return copy
}

// GetVector returnerer en kopi af den aktuelle vector
func (vc *VectorClock) GetVector() []int {
	vc.mutex.Lock()
	defer vc.mutex.Unlock()
	return vc.getCopy()
}

// Compare sammenligner to vector clocks og returnerer deres relation
// Returnerer: -1 hvis v1 < v2 (v1 happened before v2)
//             1 hvis v1 > v2 (v2 happened before v1)
//             0 hvis de er concurrent (ingen kausal relation)
func CompareVectors(v1, v2 []int) int {
	if len(v1) != len(v2) {
		panic("Vector clocks skal have samme længde!")
	}
	
	lessOrEqual := true  // Er v1 <= v2?
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
	
	// Ellers er de concurrent
	return 0
}

// VectorMessage repræsenterer en besked med Vector clock timestamp
type VectorMessage struct {
	Timestamp []int  // Vector clock når beskeden blev sendt
	ProcessID int    // ID på den proces der sendte beskeden
	Content   string // Besked-indhold
}

// String gør det nemt at printe en VectorMessage
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

// FormatVector laver en pæn string representation af en vector
func FormatVector(v []int) string {
	parts := make([]string, len(v))
	for i, val := range v {
		parts[i] = fmt.Sprintf("%d", val)
	}
	return "[" + strings.Join(parts, ",") + "]"
}
