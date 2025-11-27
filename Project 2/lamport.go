package main

import (
	"fmt"
	"sync"
)

// Lamport timestamp struct initialization
type LamportClock struct {
	time  int       // Den logiske tid
	mutex sync.Mutex // Sikrer at kun én goroutine ad gangen kan ændre time
}

// Opretter et Lamport ur med tid=0
func NewLamportClock() *LamportClock {
	return &LamportClock{
		time: 0,
	}
}

// Udfører en lokal operation
func (lc *LamportClock) LocalEvent() int {
	lc.mutex.Lock()         // Lås så andre ikke kan ændre samtidig
	defer lc.mutex.Unlock() // Unlock når funktionen er færdig
	
	lc.time++
	return lc.time
}

// Send event, increment time counter
func (lc *LamportClock) SendEvent() int {
	lc.mutex.Lock()
	defer lc.mutex.Unlock()
	
	lc.time++
	return lc.time
}

// Sammenlign modtaget time med egen tid, vælg max 
func (lc *LamportClock) ReceiveEvent(receivedTime int) int {
	lc.mutex.Lock()
	defer lc.mutex.Unlock()

	// Find max 
	if receivedTime > lc.time {
		lc.time = receivedTime
	}
	lc.time++
	return lc.time
}

// Retuner tid
func (lc *LamportClock) GetTime() int {
	lc.mutex.Lock()
	defer lc.mutex.Unlock()
	return lc.time
}

// Lamport message struct initialization
type LamportMessage struct {
	Timestamp int    // Lamport tiden når beskeden blev sendt
	ProcessID int    // ID på den proces der sendte beskeden
	Content   string // Selve besked-indholdet
}

// Print funktion
func (msg LamportMessage) String() string {
	return fmt.Sprintf("P%d@T%d: %s", msg.ProcessID, msg.Timestamp, msg.Content)
}
