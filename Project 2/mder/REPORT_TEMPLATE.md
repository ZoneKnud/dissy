# Rapport Template - Logical Clocks Project

Brug denne template til at skrive din projekt rapport.

---

# Lamport Timestamps og Vector Clocks: Design, Implementation og Evaluering

**Forfatter:** [Dit navn]  
**Kursus:** Distribuerede Systemer  
**Institution:** [Din universitet]  
**Dato:** November 2025

---

## Abstract

_Skriv 150-250 ord der opsummerer hele rapporten:_
- Hvad er problemet?
- Hvad har du implementeret?
- Hvad er de vigtigste resultater?
- Hvad er konklusionen?

---

## 1. Introduktion

### 1.1 Motivation
Hvorfor er ordering af events vigtigt i distribuerede systemer?

_Eksempler:_
- Banking: Concurrent transactions
- Distributed databases: Conflict resolution
- Collaborative editing: Concurrent edits

### 1.2 Problem Statement
_Kopier problem statement fra opgaven._

### 1.3 Mål
- Implementere Lamport timestamps
- Implementere Vector clocks
- Sammenligne algoritmerne objektivt
- Evaluere mod state of the art

### 1.4 Rapport Struktur
_Kort oversigt over resten af rapporten._

---

## 2. Baggrund og Relateret Arbejde

### 2.1 Tid i Distribuerede Systemer
- **Physical clocks**: Hvorfor virker de ikke?
  - Clock drift
  - Synchronization overhead
  - Network latency

- **Logical clocks**: Hvad er alternativet?
  - Tæl events i stedet for tid
  - Happened-before relation (→)

### 2.2 Happened-Before Relation
Definition af Lamport's happened-before relation:

```
Event a → b (a happened before b) hvis:
1. a og b er i samme proces og a kommer før b, ELLER
2. a er send event og b er modtaget receive event, ELLER
3. Der findes c sådan at a → c og c → b (transitivitet)
```

### 2.3 Partial vs Total Ordering
- **Partial ordering**: Nogle events kan ikke sammenlignes (concurrent)
- **Total ordering**: Alle events kan sammenlignes

### 2.4 Lamport Timestamps (1978)
_Forklar oprindelig paper:_
- Simpel counter-baseret løsning
- Opnår partial ordering
- Kan ikke detektere concurrency

### 2.5 Vector Clocks (1988)
_Forklar Fidge's paper:_
- Generalisering af Lamport
- Array af counters (én per proces)
- Opnår total ordering
- Kan detektere concurrency

### 2.6 State of the Art
_Moderne alternativer:_

**Hybrid Logical Clocks (HLC):**
- Kombinerer fysisk tid med logisk
- Brugt i Google Spanner
- Bedre for menneskelæsbarhed

**Dotted Version Vectors:**
- Optimering af vector clocks
- Reducerer plads overhead
- Brugt i moderne key-value stores

**Interval Tree Clocks:**
- Dynamisk antal processer
- O(log n) overhead i stedet for O(n)
- For miljøer med mange kortlivede processer

---

## 3. Design

### 3.1 Overordnet Arkitektur
_Diagram af systemet:_

```
┌─────────────────────────────────────┐
│       Simulation Framework          │
│  ┌───────────┐    ┌───────────┐   │
│  │ Process 0 │    │ Process 1 │   │
│  │ ┌───────┐ │    │ ┌───────┐ │   │
│  │ │Lamport│ │    │ │Lamport│ │   │
│  │ │Vector │ │    │ │Vector │ │   │
│  │ └───────┘ │    │ └───────┘ │   │
│  └─────┬─────┘    └─────┬─────┘   │
│        │                 │          │
│        └────── Msg ──────┘          │
│                                     │
│  ┌─────────────────────────────┐  │
│  │  Benchmark & Metrics        │  │
│  └─────────────────────────────┘  │
└─────────────────────────────────────┘
```

### 3.2 Lamport Clock Design
**Data struktur:**
```go
type LamportClock struct {
    time  int
    mutex sync.Mutex
}
```

**Algoritme:**
```
LocalEvent(): time++
SendEvent(): time++, return time
ReceiveEvent(t): time = max(time, t) + 1
```

**Design valg:**
- Single integer for simplicity
- Mutex for thread-safety
- Copy-on-read for immutability

### 3.3 Vector Clock Design
**Data struktur:**
```go
type VectorClock struct {
    vector    []int
    processID int
    mutex     sync.Mutex
}
```

**Algoritme:**
```
LocalEvent(): vector[processID]++
SendEvent(): vector[processID]++, return copy(vector)
ReceiveEvent(v): 
    for i in 0..n:
        vector[i] = max(vector[i], v[i])
    vector[processID]++
```

**Design valg:**
- Dynamic array (slice) for flexibility
- Process ID embedded for convenience
- Element-wise maximum for merging

### 3.4 Simulation Design
**Komponenter:**
- `Process`: Simulerer en distribueret proces
- `Event`: Repræsenterer en hændelse
- `Simulation`: Orkestrerer hele systemet

**Kommunikation:**
- Go channels til message passing
- Goroutines til concurrency
- Buffered channels for asynchrony

---

## 4. Implementation

### 4.1 Programmeringssprog: Go
**Hvorfor Go?**
- Native support for concurrency (goroutines)
- Channels for message passing
- Enkel syntax (læsbart for C/Python programmører)
- Compiled (hurtig execution)

### 4.2 Lamport Implementation
_Uddrag fra lamport.go med forklaring:_

```go
func (lc *LamportClock) ReceiveEvent(receivedTime int) int {
    lc.mutex.Lock()
    defer lc.mutex.Unlock()
    
    if receivedTime > lc.time {
        lc.time = receivedTime
    }
    lc.time++
    return lc.time
}
```

**Forklaring:**
1. Lock for thread-safety
2. Take maximum (synchronization)
3. Increment (event happened)
4. Return new timestamp

### 4.3 Vector Implementation
_Uddrag fra vector.go med forklaring:_

```go
func (vc *VectorClock) ReceiveEvent(receivedVector []int) []int {
    vc.mutex.Lock()
    defer vc.mutex.Unlock()
    
    for i := 0; i < len(vc.vector); i++ {
        if receivedVector[i] > vc.vector[i] {
            vc.vector[i] = receivedVector[i]
        }
    }
    vc.vector[vc.processID]++
    return vc.getCopy()
}
```

**Forklaring:**
1. Lock for thread-safety
2. Element-wise maximum (merge knowledge)
3. Increment own counter (event happened)
4. Return copy (immutability)

### 4.4 Comparison Function
_Uddrag fra vector.go:_

```go
func CompareVectors(v1, v2 []int) int {
    lessOrEqual := true
    greaterOrEqual := true
    
    for i := 0; i < len(v1); i++ {
        if v1[i] > v2[i] {
            lessOrEqual = false
        }
        if v1[i] < v2[i] {
            greaterOrEqual = false
        }
    }
    
    if lessOrEqual && !greaterOrEqual {
        return -1  // v1 < v2
    }
    if greaterOrEqual && !lessOrEqual {
        return 1   // v1 > v2
    }
    return 0       // concurrent
}
```

**Kompleksitet:** O(n) hvor n = antal processer

### 4.5 Simulation Framework
_Forklaring af Process og Simulation structs._

### 4.6 Benchmarking System
_Forklaring af hvordan metrics måles._

---

## 5. Evaluering

### 5.1 Test Metodologi
**Unit Tests:**
- Test basic functionality
- Test happened-before relation
- Test concurrency detection
- Test edge cases

**Integration Tests:**
- Run full scenarios
- Verify correct behavior

**Benchmarks:**
- Measure time complexity
- Measure space complexity
- Measure message overhead

### 5.2 Correctness Testing
**Test results:**

```
=== RUN   TestLamportClock
--- PASS: TestLamportClock (0.00s)
=== RUN   TestVectorClock
--- PASS: TestVectorClock (0.00s)
=== RUN   TestCompareVectors
--- PASS: TestCompareVectors (0.00s)
...
PASS
ok      logical-clocks  0.123s
```

**Konklusioner:**
- Alle tests passerer ✅
- Begge algoritmer implementeret korrekt
- Concurrency detection virker

### 5.3 Performance Benchmarks

**Scenario 1: 5 processer, 10 events hver**

| Metric | Lamport | Vector | Overhead |
|--------|---------|--------|----------|
| Execution Time | 50ms | 75ms | +50% |
| Memory | 2 KB | 5 KB | +150% |
| Message Size | 8 bytes | 40 bytes | +400% |
| Ordering | 75% | 100% | +25% |

**Scenario 2: 10 processer, 10 events hver**

| Metric | Lamport | Vector | Overhead |
|--------|---------|--------|----------|
| Execution Time | 55ms | 120ms | +118% |
| Memory | 2 KB | 10 KB | +400% |
| Message Size | 8 bytes | 80 bytes | +900% |
| Ordering | 75% | 100% | +25% |

### 5.4 Scalability Analysis

**Observation:**
Vector clock overhead vokser lineært med antal processer.

```
Message overhead:
Lamport: O(1) = konstant 8 bytes
Vector:  O(n) = 8n bytes

For n=100: Vector = 800 bytes per besked!
```

**Graph:** _(Lav et plot af message size vs. antal processer)_

### 5.5 Concurrency Detection Demonstration

**Test case:**
```
P0: event A
P2: event B (concurrent med A)

Lamport: A=1, B=1 → A < B? B < A? Unclear!
Vector:  A=[1,0,0], B=[0,0,1] → Concurrent! ✓
```

**Conclusion:** Vector clocks kan detektere concurrency, Lamport kan ikke.

---

## 6. Diskussion

### 6.1 Lamport Strengths
✅ Simpel at implementere  
✅ Lav overhead (tid, plads, beskeder)  
✅ Skalerer godt med mange processer  
✅ Tilstrækkelig for mange use cases  

### 6.2 Lamport Limitations
❌ Kun partial ordering  
❌ Kan ikke detektere concurrency  
❌ Ikke nok til conflict resolution  

### 6.3 Vector Strengths
✅ Total ordering  
✅ Kan detektere concurrency  
✅ Fuld kausal information  
✅ Perfekt til conflict resolution  

### 6.4 Vector Limitations
❌ O(n) overhead per besked  
❌ Skalerer dårligt (>50-100 processer)  
❌ Kræver kendt antal processer  

### 6.5 Trade-offs
**Correctness vs. Efficiency:**
- Lamport: Hurtig men limited
- Vector: Fuld funktionalitet men dyr

**When to use what?**
- Lamport: Logging, debugging, simple ordering
- Vector: Databases, collaborative editing, CRDTs

### 6.6 State of the Art Comparison

**Hybrid Logical Clocks (HLC):**
- Combines physical + logical time
- Better than Lamport (has physical time)
- Better than Vector (O(1) overhead)
- Men: Kræver bounded clock drift

**Dotted Version Vectors:**
- Optimized vector clocks
- Only send relevant entries
- Reducerer overhead betydeligt

**Interval Tree Clocks:**
- Dynamic process set
- O(log n) overhead
- Kompleks at implementere

### 6.7 Limitations of This Study
- Simplified simulation (no real network)
- No fault tolerance
- No dynamic process joins/leaves
- Synthetic workload

---

## 7. Konklusion

### 7.1 Opsummering
_Opsummer hele projektet i 1 paragraf._

### 7.2 Bidrag
Dette projekt har:
1. Implementeret både Lamport og Vector clocks i Go
2. Lavet comprehensive benchmark comparison
3. Demonstreret trade-offs mellem correctness og overhead
4. Sammenlinet med state of the art

### 7.3 Key Findings
1. **Lamport er O(1), Vector er O(n)** - Signifikant forskel i overhead
2. **Vector kan detektere concurrency** - Kritisk for nogle use cases
3. **Trade-off er real** - Ingen "best" algoritme, depends on use case
4. **Modern alternatives exist** - HLC og DVV løser nogle problemer

### 7.4 Fremtidig Arbejde
- Implementer Hybrid Logical Clocks
- Tilføj network latency simulation
- Test med større antal processer (100+)
- Implementer fault tolerance
- Visualisering af happened-before graphs

---

## 8. Referencer

[1] Lamport, L. (1978). "Time, Clocks, and the Ordering of Events in a Distributed System". Communications of the ACM, 21(7), 558-565.

[2] Fidge, C. J. (1988). "Timestamps in Message-Passing Systems That Preserve the Partial Ordering". Proceedings of the 11th Australian Computer Science Conference, 56-66.

[3] Mattern, F. (1988). "Virtual Time and Global States of Distributed Systems". Parallel and Distributed Algorithms, 215-226.

[4] Kulkarni, S. S., et al. (2014). "Logical Physical Clocks and Consistent Snapshots in Globally Distributed Databases". OSDI.

[5] Almeida, P. S., et al. (2015). "Dotted Version Vectors: Logical Clocks for Optimistic Replication". arXiv preprint arXiv:1011.5808.

[6] Almeida, P. S., et al. (2008). "Interval Tree Clocks: A Logical Clock for Dynamic Systems". International Conference on Principles of Distributed Systems.

---

## Appendix A: Kode Listings

_Inkluder udvalgte dele af koden hvis relevant._

## Appendix B: Test Resultater

_Inkluder fuld test output._

## Appendix C: Benchmark Data

_Inkluder rådata fra benchmarks._

---

## Tips til Rapportskrivning

### Do's:
✅ Brug tekniske termer korrekt  
✅ Inkluder diagrammer og plots  
✅ Begrund alle design valg  
✅ Diskuter limitations ærligt  
✅ Sammenlign objektivt med state of the art  
✅ Cite kilder korrekt  

### Don'ts:
❌ Påstå at én algoritme er "bedst" (det afhænger af use case!)  
❌ Ignorere overhead costs  
❌ Glemme at diskutere limitations  
❌ Kopiere kode uden forklaring  
❌ Glemme at konkludere klart  

### Struktur Tips:
- **Hver sektion** skal have indledning og konklusion
- **Figurer** skal have captions og refereres i tekst
- **Tabeller** skal være letlæselige og have headers
- **Kode** skal have kommentarer og forklaring
- **Grafer** skal have labels på akser

### Sprog Tips:
- Brug **aktiv form** når muligt: "Vi implementerede" ikke "Der blev implementeret"
- Brug **præsens** for facts: "Lamport clocks er O(1)"
- Brug **datid** for hvad du gjorde: "Vi målte overhead"
- Vær **præcis**: "75% hurtigere" ikke "meget hurtigere"

---

**God fornøjelse med rapporten! 📝**
