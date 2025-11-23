package main

import (
	"fmt"
	"sync"
)

// LamportClock er en simpel logisk ur implementation
// Den holder styr på en enkelt counter værdi
type LamportClock struct {
	time  int       // Den logiske tid
	mutex sync.Mutex // Sikrer at kun én goroutine ad gangen kan ændre time
}

// NewLamportClock opretter et nyt Lamport ur der starter ved 0
func NewLamportClock() *LamportClock {
	return &LamportClock{
		time: 0,
	}
}

// LocalEvent kaldes når processen udfører en lokal operation
// Den øger den logiske tid med 1
func (lc *LamportClock) LocalEvent() int {
	lc.mutex.Lock()         // Lås så andre ikke kan ændre samtidig
	defer lc.mutex.Unlock() // Unlock når funktionen er færdig
	
	lc.time++
	return lc.time
}

// SendEvent kaldes før en besked sendes til en anden proces
// Den øger tiden og returnerer timestamp der skal sendes med beskeden
func (lc *LamportClock) SendEvent() int {
	lc.mutex.Lock()
	defer lc.mutex.Unlock()
	
	lc.time++
	return lc.time
}

// ReceiveEvent kaldes når en besked modtages fra en anden proces
// Den synkroniserer uret med afsenderens tid ved at tage max af de to
// Dette sikrer kausal ordering: hvis event A -> B, så time(A) < time(B)
func (lc *LamportClock) ReceiveEvent(receivedTime int) int {
	lc.mutex.Lock()
	defer lc.mutex.Unlock()
	
	// Find den største af vores tid og modtaget tid
	if receivedTime > lc.time {
		lc.time = receivedTime
	}
	
	// Øg med 1 for receive event
	lc.time++
	return lc.time
}

// GetTime returnerer den nuværende logiske tid (bruges til debugging)
func (lc *LamportClock) GetTime() int {
	lc.mutex.Lock()
	defer lc.mutex.Unlock()
	return lc.time
}

// LamportMessage repræsenterer en besked med Lamport timestamp
type LamportMessage struct {
	Timestamp int    // Lamport tiden når beskeden blev sendt
	ProcessID int    // ID på den proces der sendte beskeden
	Content   string // Selve besked-indholdet
}

// String gør det nemt at printe en LamportMessage
func (msg LamportMessage) String() string {
	return fmt.Sprintf("P%d@T%d: %s", msg.ProcessID, msg.Timestamp, msg.Content)
}
