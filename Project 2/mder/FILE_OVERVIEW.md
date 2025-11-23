# Fil Oversigt - Logical Clocks Project

## 📁 Projekt Struktur

```
Project 2/
├── main.go              - Hovedprogram (entry point)
├── lamport.go           - Lamport timestamp implementation
├── vector.go            - Vector clock implementation
├── simulation.go        - Distribueret system simulation
├── benchmark.go         - Performance metrics og sammenligning
├── clocks_test.go       - Unit tests og benchmarks
├── go.mod               - Go module definition
├── README.md            - Projekt dokumentation
├── EXPLANATION.md       - Detaljeret forklaring af kode
└── VISUAL_EXAMPLES.md   - Visuelle eksempler og use cases
```

## 📄 Fil Beskrivelser

### `main.go` (Entry Point)
**Hvad gør den:** Kører alle demonstrations
- Demo 1: Lamport clock simulation med 3 processer
- Demo 2: Vector clock simulation med 3 processer
- Demo 3: Concurrency detection demonstration
- Demo 4: Performance benchmark (5 processer)
- Demo 5: Scalability test (10 processer)

**Kør den:**
```bash
go run .
```

---

### `lamport.go` (Lamport Implementation)
**Hvad indeholder den:**
- `LamportClock` struct
  - `time`: Den logiske tid (integer)
  - `mutex`: Thread-safety lock
  
- Metoder:
  - `NewLamportClock()`: Opret ny clock
  - `LocalEvent()`: Håndter lokal event
  - `SendEvent()`: Håndter send event
  - `ReceiveEvent(receivedTime)`: Håndter receive og synkroniser
  - `GetTime()`: Hent nuværende tid

- `LamportMessage` struct: Repræsentation af en besked med timestamp

**Kompleksitet:**
- Tid: O(1) per operation
- Plads: O(1) per proces

---

### `vector.go` (Vector Clock Implementation)
**Hvad indeholder den:**
- `VectorClock` struct
  - `vector`: Array af integers (én per proces)
  - `processID`: Denne proces' ID
  - `mutex`: Thread-safety lock

- Metoder:
  - `NewVectorClock(numProcesses, processID)`: Opret ny clock
  - `LocalEvent()`: Øg egen counter
  - `SendEvent()`: Øg egen counter og returner vector
  - `ReceiveEvent(receivedVector)`: Merge vectors
  - `GetVector()`: Hent kopi af vector

- `CompareVectors(v1, v2)`: Sammenlign to vectors
  - Returnerer: -1 (v1 < v2), 0 (concurrent), 1 (v1 > v2)

- `VectorMessage` struct: Besked med vector timestamp

**Kompleksitet:**
- Tid: O(n) per operation (n = antal processer)
- Plads: O(n) per proces

---

### `simulation.go` (Simulation Framework)
**Hvad indeholder den:**
- `Event` struct: Repræsenterer en hændelse
- `Process` struct: Simulerer en distribueret proces
  - Holder både Lamport og Vector clock
  - Har en MessageQueue (Go channel)
  - Logger alle events

- Metoder på Process:
  - `NewProcess()`: Opret ny proces
  - `HandleLocalEvent()`: Udfør lokal operation
  - `SendMessage()`: Send besked til anden proces
  - `ReceiveMessage()`: Håndter modtaget besked
  - `Run()`: Start proces (kører i goroutine)

- `Simulation` struct: Håndterer hele systemet
  - `NewSimulation(numProcesses, useVectorClock)`: Opret simulation
  - `RunScenario()`: Kør forudbestemt scenario
  - `PrintLogs()`: Vis event logs

**Use case:** Test algoritmer i et realistisk miljø

---

### `benchmark.go` (Performance Metrics)
**Hvad indeholder den:**
- `Metrics` struct: Holder performance data
  - ClockType (Lamport/Vector)
  - NumProcesses, NumEvents
  - TotalExecutionTime
  - MemoryUsed
  - MessageOverhead
  - OrderingCorrectness

- Funktioner:
  - `RunBenchmark(numProcesses, numEvents)`: Kør fuld benchmark
  - `benchmarkAlgorithm()`: Mål én algoritme
  - `calculateOrderingCorrectness()`: Beregn hvor mange events kan ordnes
  - `PrintMetrics()`: Vis resultater pænt
  - `CompareResults()`: Sammenlign Lamport vs Vector
  - `DemonstrateConcurrency()`: Vis forskellen i concurrency detection

**Output:** Detaljeret sammenligning af overhead og capabilities

---

### `clocks_test.go` (Tests)
**Hvad indeholder den:**

**Unit Tests:**
- `TestLamportClock()`: Test basic Lamport funktionalitet
- `TestVectorClock()`: Test basic Vector funktionalitet
- `TestCompareVectors()`: Test vector comparison
- `TestLamportHappenedBefore()`: Verificer happened-before
- `TestVectorConcurrency()`: Verificer concurrency detection
- `TestVectorCausalRelation()`: Verificer causal relation

**Benchmarks:**
- `BenchmarkLamportLocalEvent()`: Mål Lamport hastighed
- `BenchmarkLamportReceive()`: Mål Lamport receive
- `BenchmarkVectorLocalEvent()`: Mål Vector hastighed
- `BenchmarkVectorReceive()`: Mål Vector receive
- `BenchmarkCompareVectors()`: Mål comparison hastighed

**Kør tests:**
```bash
go test              # Kør alle tests
go test -v           # Verbose output
go test -bench=.     # Kør benchmarks
go test -cover       # Med code coverage
```

---

### `go.mod` (Module Definition)
**Hvad er det:** Go's dependency management fil
- Definerer module navnet: `logical-clocks`
- Specificerer Go version: 1.21
- Ingen eksterne dependencies (bruger kun standard library)

---

### `README.md` (Projekt Dokumentation)
**Indhold:**
- Installation instruktioner (hvordan installere Go)
- Projekt oversigt
- Forklaring af Lamport og Vector clocks
- Sammenligningstabel
- State of the art sammenligning
- Use cases og anbefalinger

**Target audience:** Andre der skal forstå projektet

---

### `EXPLANATION.md` (Detaljeret Kode Forklaring)
**Indhold:**
- Problemet vi løser
- Gennemgang af Lamport implementation (kode-by-kode)
- Gennemgang af Vector implementation
- Simulation framework forklaring
- Benchmarking forklaring
- Go koncepter forklaret (pointers, methods, channels, goroutines)
- Testing i Go

**Target audience:** Dig! For at forstå hvordan koden virker

---

### `VISUAL_EXAMPLES.md` (Visuelle Eksempler)
**Indhold:**
- 5 detaljerede eksempler med diagrammer
- Sammenligning af Lamport vs Vector på samme scenarios
- Overhead scaling analysis
- Når skal man bruge hvad?
- Real-world use cases

**Target audience:** For at forstå koncepterne visuelt

---

## 🚀 Quick Start Guide

### 1. Installér Go
```bash
brew install go  # macOS
```

### 2. Verificer installation
```bash
go version
```

### 3. Kør projektet
```bash
cd "Project 2"
go run .
```

### 4. Kør tests
```bash
go test -v
```

### 5. Kør benchmarks
```bash
go test -bench=.
```

---

## 📊 Forventede Resultater

Når du kører `go run .`, vil du se:

1. **Lamport Simulation Logs:**
   ```
   P0: Local event T1: Event A
   P0: Send to P1 at T2: Message from P0
   P1: Receive from P0 at T3: Message from P0
   ...
   ```

2. **Vector Simulation Logs:**
   ```
   P0: Local event [1,0,0]: Event A
   P0: Send to P1 at [2,0,0]: Message from P0
   P1: Receive from P0 at [2,1,0]: Message from P0
   ...
   ```

3. **Concurrency Detection:**
   ```
   Lamport kan IKKE detektere concurrent events
   Vector clock KAN detektere concurrent events!
   ```

4. **Benchmark Results:**
   ```
   --- Lamport Metrics ---
   Execution Time:      50ms
   Memory Used:         2048 bytes
   Message Overhead:    8 bytes per message
   
   --- Vector Metrics ---
   Execution Time:      75ms
   Memory Used:         5120 bytes
   Message Overhead:    40 bytes per message (5 processes)
   ```

---

## 🎓 Læringsmål Opfyldt

Efter at have gennemgået dette projekt, burde du kunne:

### Distribuerede Systemer:
✅ Forklare hvorfor fysiske ure ikke virker i distribuerede systemer  
✅ Forstå happened-before relation (→)  
✅ Implementere Lamport timestamps  
✅ Implementere Vector clocks  
✅ Sammenligne partial vs total ordering  
✅ Detektere concurrent events  
✅ Forstå trade-offs mellem correctness og overhead  

### Go Programmering:
✅ Oprette structs og methods  
✅ Bruge pointers korrekt  
✅ Implementere thread-safe kode med mutexes  
✅ Bruge channels til kommunikation  
✅ Starte goroutines (concurrent execution)  
✅ Skrive unit tests  
✅ Lave benchmarks  

---

## 📚 Næste Skridt

1. **Kør projektet** og se output
2. **Læs EXPLANATION.md** for at forstå koden
3. **Læs VISUAL_EXAMPLES.md** for at forstå koncepterne
4. **Modificer koden** - prøv at ændre antal processer
5. **Tilføj features** - fx network latency simulation
6. **Skriv rapport** baseret på README.md

---

## 🔧 Troubleshooting

**Problem:** `go: command not found`  
**Løsning:** Installér Go først (se README.md)

**Problem:** Import errors  
**Løsning:** Kør `go mod tidy` for at fikse dependencies

**Problem:** Tests fejler  
**Løsning:** Tjek at alle .go filer er i samme directory

**Problem:** Kan ikke forstå koden  
**Løsning:** Læs EXPLANATION.md linje-for-linje

---

**God fornøjelse med projektet! 🎉**
