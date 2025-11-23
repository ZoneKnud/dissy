# Detaljeret Forklaring: Lamport Timestamps og Vector Clocks

## 🎯 Problemet Vi Løser

I et distribueret system har hver computer sit eget ur, men de kan ikke stole på at være synkroniserede. Vi har brug for en måde at bestemme rækkefølgen af events uden fysiske ure.

**Eksempel scenario:**
```
Tid: 10:00:01  P0: Alice sender "Hej"
Tid: 10:00:00  P1: Bob sender "Hej tilbage"
```

Selvom Alice' ur viser 10:00:01 og Bob's ur viser 10:00:00, kan vi ikke konkludere at Bob svarede før Alice sendte! Måske er Bob's ur bare galt.

**Løsning:** Brug **logiske ure** i stedet for fysiske.

---

## 📖 Del 1: Lamport Timestamps - Den Simple Løsning

### Grundidé

Lamport foreslog: "Lad os tælle events i stedet for at måle tid!"

**Regler:**
1. Hver proces har en counter der starter ved 0
2. Ved enhver event: øg counter med 1
3. Ved beskeder: send din counter med, og modtageren synkroniserer

### Kode-gennemgang: `lamport.go`

```go
type LamportClock struct {
    time  int         // Vores counter
    mutex sync.Mutex  // Sikrer thread-safety
}
```

**Hvorfor `mutex`?**
I Go kan flere goroutines (lightweight threads) køre samtidigt. Hvis to goroutines prøver at ændre `time` samtidigt, får vi race conditions. En `mutex` (mutual exclusion lock) sikrer at kun én goroutine ad gangen kan ændre `time`.

```go
func (lc *LamportClock) LocalEvent() int {
    lc.mutex.Lock()         // "Jeg låser døren, I andre må vente"
    defer lc.mutex.Unlock() // "Når jeg er færdig, låser jeg op"
    
    lc.time++
    return lc.time
}
```

**`defer`** er Go's måde at sige "gør dette når funktionen slutter, uanset hvordan den slutter". Det sikrer at vi altid unlcker, selv hvis der sker en fejl.

### Send og Receive

```go
func (lc *LamportClock) SendEvent() int {
    lc.mutex.Lock()
    defer lc.mutex.Unlock()
    
    lc.time++           // Øg vores tid
    return lc.time      // Send denne værdi med beskeden
}

func (lc *LamportClock) ReceiveEvent(receivedTime int) int {
    lc.mutex.Lock()
    defer lc.mutex.Unlock()
    
    // Tag max af vores tid og modtaget tid
    if receivedTime > lc.time {
        lc.time = receivedTime
    }
    
    lc.time++           // Øg efter synkronisering
    return lc.time
}
```

**Hvorfor `max`?**
Dette sikrer at hvis modtageren "er bagud", synkroniserer den sig. Det sikrer egenskaben: hvis event A sendte til event B, så time(A) < time(B).

### Eksempel

```
P0: start (T=0)
P0: local event (T=1)
P0: send til P1 (T=2, sender "2")

P1: start (T=0)
P1: local event (T=1)
P1: receive fra P0 ("2") → max(1,2)+1 = 3 (T=3)
P1: local event (T=4)
```

**Problem:** Hvis P1 havde T=5 da den modtog, ville vi få:
- P0 send: T=2
- P1 receive: T=6

T=2 < T=6, så det ser ud som om P0's send skete før P1's receive. **Korrekt!**

Men hvis to events har forskellige timestamps, kan vi ikke altid konkludere hvem der skete først - de kan være concurrent!

---

## 🔬 Del 2: Vector Clocks - Den Kraftfulde Løsning

### Grundidé

I stedet for én counter, har hver proces et array af counters - én for hver proces.

**Format:** `[P0's tid, P1's tid, P2's tid, ...]`

Dette giver os "bredere perspektiv" - vi ved ikke kun vores egen tid, men hvad vi ved om alle andre processer.

### Kode-gennemgang: `vector.go`

```go
type VectorClock struct {
    vector    []int      // Array af counters
    processID int        // Vores eget ID
    mutex     sync.Mutex
}
```

**Slice vs Array i Go:**
- Array: `[3]int` - fast størrelse
- Slice: `[]int` - dynamisk størrelse (ligesom Python lists)

Vi bruger slices fordi vi vil kunne ændre antal processer.

### Operationer

```go
func (vc *VectorClock) LocalEvent() []int {
    vc.mutex.Lock()
    defer vc.mutex.Unlock()
    
    vc.vector[vc.processID]++  // Øg KUN vores egen position
    return vc.getCopy()         // Returner en kopi
}
```

**Hvorfor kopi?**
Hvis vi returnerer den originale slice, kunne andre ændre den! En kopi sikrer immutability.

### Receive Event - Den Vigtige Del

```go
func (vc *VectorClock) ReceiveEvent(receivedVector []int) []int {
    vc.mutex.Lock()
    defer vc.mutex.Unlock()
    
    // Merge: For hver position, tag maximum
    for i := 0; i < len(vc.vector); i++ {
        if receivedVector[i] > vc.vector[i] {
            vc.vector[i] = receivedVector[i]
        }
    }
    
    // Øg vores egen position
    vc.vector[vc.processID]++
    return vc.getCopy()
}
```

**Hvad sker der her?**

Lad os sige P1 modtager en besked fra P0:

```
P0 sender: [5, 2, 3]  (P0 har set 5 events hos sig selv, 2 hos P1, 3 hos P2)
P1 har:    [4, 8, 1]  (P1 har set 4 hos P0, 8 hos sig selv, 1 hos P2)

Merge:
  Position 0: max(4, 5) = 5  ← P1 lærer at P0 faktisk er ved 5
  Position 1: max(8, 2) = 8  ← P1's egen viden er nyere
  Position 2: max(1, 3) = 3  ← P1 lærer at P2 er ved 3

P1 efter:  [5, 9, 3]  (position 1 øget for receive event)
```

### Sammenligning af Vectors

```go
func CompareVectors(v1, v2 []int) int {
    lessOrEqual := true     // Er v1 <= v2 i alle positioner?
    greaterOrEqual := true  // Er v1 >= v2 i alle positioner?
    
    for i := 0; i < len(v1); i++ {
        if v1[i] > v2[i] {
            lessOrEqual = false
        }
        if v1[i] < v2[i] {
            greaterOrEqual = false
        }
    }
    
    if lessOrEqual && !greaterOrEqual {
        return -1  // v1 happened before v2
    }
    if greaterOrEqual && !lessOrEqual {
        return 1   // v2 happened before v1
    }
    return 0       // concurrent eller identiske
}
```

**Logikken:**

- **v1 < v2** (happened before): Alle positioner i v1 ≤ v2, og mindst én er strict mindre
- **v1 > v2** (happened after): Alle positioner i v1 ≥ v2, og mindst én er strict større
- **v1 || v2** (concurrent): Nogle positioner er større i v1, andre større i v2

**Eksempel:**

```
[1, 2, 3] og [2, 3, 4]  →  [1,2,3] < [2,3,4]  (happened before)
[2, 3, 4] og [1, 2, 3]  →  [2,3,4] > [1,2,3]  (happened after)
[1, 3, 2] og [2, 2, 3]  →  concurrent! (1<2 men 3>2)
```

---

## 🏗️ Del 3: Simulation Framework

### Process Struktur

```go
type Process struct {
    ID            int
    LamportClock  *LamportClock
    VectorClock   *VectorClock
    EventLog      []string
    MessageQueue  chan Event      // Go channel
    UseVectorClock bool
}
```

**Go Channels:**
Channels er Go's måde at kommunikere mellem goroutines. Tænk på det som en "pipe":

```go
ch := make(chan Event, 100)  // Buffered channel (kan holde 100 beskeder)

// Sender:
ch <- event  // Put event i pipen

// Receiver:
event := <-ch  // Tag event fra pipen
```

Hvis pipen er fuld, blokerer senderen. Hvis pipen er tom, blokerer modtageren. Dette er "synchronization via communication".

### Send og Receive Messages

```go
func (p *Process) SendMessage(target *Process, message string) {
    if p.UseVectorClock {
        vector := p.VectorClock.SendEvent()
        
        // Send til target's queue
        target.MessageQueue <- Event{
            Type:      "receive",
            ProcessID: p.ID,
            Message:   fmt.Sprintf("%s|%s", FormatVector(vector), message),
        }
    } else {
        timestamp := p.LamportClock.SendEvent()
        
        target.MessageQueue <- Event{
            Type:      "receive",
            ProcessID: p.ID,
            Message:   fmt.Sprintf("%d|%s", timestamp, message),
        }
    }
}
```

**Hvad sker der?**
1. Vi kalder clock's SendEvent (øger vores tid)
2. Vi laver en Event struct med timestamp og besked
3. Vi sender Event'en til target's MessageQueue channel
4. Target vil modtage den asynkront

### Process Run Loop

```go
func (p *Process) Run(done chan bool) {
    go func() {  // Start en ny goroutine
        for {
            select {  // Go's "switch" for channels
            case event := <-p.MessageQueue:
                p.ReceiveMessage(event)
            case <-done:
                return  // Stop goroutine
            case <-time.After(100 * time.Millisecond):
                continue  // Timeout
            }
        }
    }()
}
```

**`select` statement:**
Go's `select` er som en switch, men for channels. Den venter på den første channel der er klar:

- Hvis der kommer en besked i `MessageQueue`, håndter den
- Hvis `done` channel lukkes, stop goroutinen
- Hvis ingen sker i 100ms, continue (undgår infinite hang)

---

## 📊 Del 4: Benchmarking

### Memory Measurement

```go
var memBefore runtime.MemStats
runtime.GC()                      // Force garbage collection
runtime.ReadMemStats(&memBefore)  // Læs memory stats

// ... kør kode ...

var memAfter runtime.MemStats
runtime.ReadMemStats(&memAfter)
memoryUsed := memAfter.Alloc - memBefore.Alloc
```

**Go's Garbage Collector:**
Go har automatisk memory management (ligesom Python). `runtime.GC()` tvinger garbage collectoren til at køre nu, så vi får mere præcise målinger.

### Message Overhead Calculation

```go
var messageOverhead int
if useVectorClock {
    messageOverhead = numProcesses * 8  // 8 bytes per int
} else {
    messageOverhead = 8  // Single int
}
```

**Hvorfor 8 bytes?**
I Go (på 64-bit systemer) er en `int` = `int64` = 8 bytes.

Vector clock sender hele arrayet: `n * 8 bytes`
Lamport sender bare ét tal: `8 bytes`

Dette viser hvordan overhead skalerer med antal processer!

---

## 🎓 Hvad Gør Hvert Go Koncept?

### 1. Pointers (`*` og `&`)

```go
func NewLamportClock() *LamportClock {  // Returner pointer
    return &LamportClock{time: 0}       // & = "adressen af"
}

clock := NewLamportClock()  // clock er en pointer
clock.LocalEvent()           // Go auto-dereferencer (ingen -> nødvendig!)
```

I C ville vi skrive `clock->LocalEvent()`, men Go gør det automatisk.

### 2. Methods vs Functions

```go
// Function
func DoSomething(clock *LamportClock) {
    clock.time++
}

// Method (Go's måde)
func (clock *LamportClock) DoSomething() {
    clock.time++
}

// Brug:
clock.DoSomething()  // Pænere syntax!
```

### 3. Struct Initialization

```go
// Named fields (anbefalet)
clock := &LamportClock{
    time: 0,
    mutex: sync.Mutex{},
}

// Eller kort form hvis zero values er ok
clock := &LamportClock{}  // time = 0 automatisk
```

### 4. Slices

```go
// Make et slice med længde 5
v := make([]int, 5)  // [0, 0, 0, 0, 0]

// Access
v[0] = 10

// Append (dynamisk vækst)
v = append(v, 20)  // [10, 0, 0, 0, 0, 20]

// Length
len(v)  // 6

// Copy
copy := make([]int, len(v))
for i := range v {
    copy[i] = v[i]
}
```

### 5. Goroutines og Channels

```go
// Start en goroutine
go func() {
    // Denne kode kører concurrent!
}()

// Channels for kommunikation
ch := make(chan int)

// Send (blokerer hvis channel er fuld)
ch <- 42

// Receive (blokerer hvis channel er tom)
value := <-ch
```

**Vigtigt:** Go's philosophy er "Don't communicate by sharing memory; share memory by communicating". Channels er den anbefalede måde at synkronisere.

---

## 🔍 Testing i Go

### Unit Tests (`clocks_test.go`)

```go
func TestLamportClock(t *testing.T) {  // Skal hedde Test*
    clock := NewLamportClock()
    
    if clock.GetTime() != 0 {
        t.Errorf("Forventet 0, fik %d", clock.GetTime())  // Fail test
    }
}
```

**Kør tests:**
```bash
go test          # Kør alle tests
go test -v       # Verbose output
go test -cover   # Med coverage
```

### Benchmarks

```go
func BenchmarkLamportLocalEvent(b *testing.B) {  // Skal hedde Benchmark*
    clock := NewLamportClock()
    for i := 0; i < b.N; i++ {  // b.N adjusteres automatisk
        clock.LocalEvent()
    }
}
```

**Kør benchmarks:**
```bash
go test -bench=.  # Kør alle benchmarks
```

---

## 💡 Key Takeaways

### Go Læring

1. **Pointers**: Bruges meget, men Go gør dem nemmere end C
2. **Methods**: Pæn OOP-style uden classes
3. **Goroutines**: Lightweight concurrency (meget billigere end threads)
4. **Channels**: Concurrent kommunikation done right
5. **Interfaces**: Implicit implementation (ikke i dette projekt, men vigtigt)

### Distribuerede Systemer Læring

1. **Logical clocks løser ordering uden synchronized physical clocks**
2. **Lamport: Simple, effektiv, men limited (partial ordering)**
3. **Vector: Kraftfuld, men overhead (O(n) per besked)**
4. **Trade-offs: Correctness vs Performance**
5. **Concurrency detection kræver mere information**

### Hvornår Bruges Hvad?

**Brug Lamport når:**
- Du kun skal vide om A happened before B
- Du har mange processer (overhead matters)
- Du ikke behøver at detektere concurrency

**Brug Vector når:**
- Du skal kunne detektere concurrent events
- Du har brug for total ordering
- Antal processer er moderat (< 100)
- Conflict resolution (fx i distributed databases)

**I den rigtige verden:**
- Google Spanner: Hybrid (TrueTime med fysiske ure + logiske ure)
- Riak: Vector clocks for conflict resolution
- Cassandra: Lamport-style timestamps
- Git: DAG (Directed Acyclic Graph) - relateret til vector clocks

---

**Held og lykke med projektet! 🚀**
