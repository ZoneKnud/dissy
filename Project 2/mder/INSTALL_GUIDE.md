# Installation og Setup Guide

Denne guide hjælper dig med at få projektet til at køre på din Mac.

## 📋 Forudsætninger

- macOS (du har allerede)
- Terminal adgang
- Internet forbindelse

## 🚀 Step-by-Step Installation

### Step 1: Installér Homebrew (hvis ikke allerede installeret)

Åbn Terminal og kør:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Verificer installation:
```bash
brew --version
```

### Step 2: Installér Go

```bash
brew install go
```

Dette downloader og installerer den nyeste version af Go.

### Step 3: Verificer Go Installation

```bash
go version
```

Du skulle se noget som: `go version go1.21.5 darwin/arm64`

### Step 4: Sæt Go Environment (valgfrit, men anbefalet)

Tilføj til din `~/.zshrc` fil:

```bash
echo 'export GOPATH=$HOME/go' >> ~/.zshrc
echo 'export PATH=$PATH:$GOPATH/bin' >> ~/.zshrc
source ~/.zshrc
```

### Step 5: Naviger til Projekt Mappen

```bash
cd "/Users/anders/Library/CloudStorage/OneDrive-Personal/Desktop/UNI/5. semester/Dissy/dissy/Project 2"
```

### Step 6: Verificer Alle Filer Er Der

```bash
ls -la
```

Du skulle se:
- `main.go`
- `lamport.go`
- `vector.go`
- `simulation.go`
- `benchmark.go`
- `clocks_test.go`
- `go.mod`
- `README.md`
- Flere `.md` filer

## ▶️ Kør Projektet

### Kør Hovedprogrammet

```bash
go run .
```

Eller specifikt:
```bash
go run main.go lamport.go vector.go simulation.go benchmark.go
```

**Forventet output:**
```
=================================================
   DISTRIBUTED SYSTEMS - LOGICAL CLOCKS PROJECT
   Lamport Timestamps vs Vector Clocks
=================================================

### DEMO 1: LAMPORT CLOCK SIMULATION ###
...
```

### Kør Tests

```bash
go test
```

Eller med verbose output:
```bash
go test -v
```

**Forventet output:**
```
=== RUN   TestLamportClock
--- PASS: TestLamportClock (0.00s)
=== RUN   TestVectorClock
--- PASS: TestVectorClock (0.00s)
...
PASS
ok      logical-clocks  0.123s
```

### Kør Benchmarks

```bash
go test -bench=.
```

**Forventet output:**
```
BenchmarkLamportLocalEvent-8     1000000    1234 ns/op
BenchmarkVectorLocalEvent-8       500000    2345 ns/op
...
```

### Kør Med Coverage

```bash
go test -cover
```

**Forventet output:**
```
PASS
coverage: 78.5% of statements
ok      logical-clocks  0.234s
```

## 🔧 Troubleshooting

### Problem: "go: command not found"

**Løsning:**
```bash
# Installér Go
brew install go

# Verificer
which go
go version
```

### Problem: "package logical-clocks is not in GOROOT"

**Løsning:**
```bash
# Sørg for at go.mod eksisterer
ls go.mod

# Hvis ikke, opret den:
go mod init logical-clocks
```

### Problem: "cannot find package"

**Løsning:**
```bash
# Tidy up dependencies
go mod tidy

# Eller re-init
rm go.mod go.sum
go mod init logical-clocks
```

### Problem: Tests fejler med race condition

**Løsning:**
```bash
# Kør med race detector
go test -race

# Hvis der er race conditions, er det fordi flere goroutines
# tilgår samme data. Vores kode bruger mutexes til at forhindre dette.
```

### Problem: "too many open files"

**Løsning:**
```bash
# Øg file descriptor limit
ulimit -n 4096

# Eller reducer antal processer/events i benchmarks
```

### Problem: Koden kompilerer ikke

**Tjek:**
1. Er alle `.go` filer i samme directory?
2. Har alle filer `package main` i toppen?
3. Er der syntax fejl?

**Debug:**
```bash
# Kompiler uden at køre
go build .

# Vis eventuelle fejl
```

## 📊 Forventet Output Forklaring

### Main Program Output

**Demo 1 - Lamport:**
```
P0: Local event T1: Event A
```
- `P0` = Process 0
- `T1` = Lamport timestamp 1
- `Event A` = Event navn

**Demo 2 - Vector:**
```
P0: Send to P1 at [2,0,0]: Message
```
- `[2,0,0]` = Vector clock
  - Position 0 (P0): 2
  - Position 1 (P1): 0
  - Position 2 (P2): 0

**Demo 3 - Concurrency:**
```
Lamport kan IKKE detektere concurrent events
Vector clock KAN detektere concurrent events!
```

**Demo 4 & 5 - Benchmarks:**
```
--- Lamport Metrics ---
Execution Time:      50ms
Memory Used:         2048 bytes (2.00 KB)
Message Overhead:    8 bytes per message
Ordering Capability: 75.0%
```

## 🎯 Hvad Betyder Metrics?

### Execution Time
Hvor lang tid det tog at køre alle events.
- **Lavere = bedre**

### Memory Used
Hvor meget RAM algoritmen bruger.
- **Lamport**: O(1) = ~2KB
- **Vector**: O(n) = ~5-10KB

### Message Overhead
Hvor mange bytes der sendes per besked.
- **Lamport**: 8 bytes (1 integer)
- **Vector**: 8n bytes (n integers)

### Ordering Capability
Hvor mange procent af events der kan ordnes definitivt.
- **Lamport**: ~75% (kun partial ordering)
- **Vector**: 100% (total ordering)

## 📈 Performance Tips

### Reducer Execution Time

Hvis programmet er for langsomt:

1. **Reducer antal processer:**
   ```go
   // I main.go, ændr:
   result := RunBenchmark(5, 10)  // Fra (10, 10)
   ```

2. **Reducer antal events:**
   ```go
   result := RunBenchmark(5, 5)   // Fra (5, 10)
   ```

3. **Reducer sleep times:**
   ```go
   // I simulation.go, ændr:
   time.Sleep(5 * time.Millisecond)  // Fra 10ms
   ```

### Øge Test Coverage

For at få højere test coverage:

```bash
# Se hvilke linjer der ikke er testet
go test -coverprofile=coverage.out
go tool cover -html=coverage.out
```

Dette åbner en browser med coverage visualization.

## 🔍 Debug Tips

### Print Debug Info

Tilføj debug prints i koden:

```go
// I lamport.go
func (lc *LamportClock) LocalEvent() int {
    lc.mutex.Lock()
    defer lc.mutex.Unlock()
    
    lc.time++
    fmt.Printf("[DEBUG] LocalEvent: time=%d\n", lc.time)  // Debug
    return lc.time
}
```

### Kør Specific Test

```bash
# Kør kun én test
go test -run TestLamportClock

# Kør tests der matcher pattern
go test -run TestLamport
```

### Kør Med Verbose

```bash
go test -v -run TestLamportClock
```

## 📚 Næste Skridt

1. ✅ **Kør programmet** og se at det virker
2. ✅ **Kør tests** og verificer de passerer
3. ✅ **Læs README.md** for projekt overview
4. ✅ **Læs EXPLANATION.md** for kode forklaring
5. ✅ **Læs VISUAL_EXAMPLES.md** for eksempler
6. ✅ **Modificer koden** og eksperimenter
7. ✅ **Skriv rapport** baseret på REPORT_TEMPLATE.md

## 🆘 Hvis Intet Virker

### Nuclear Option: Start Fra Scratch

```bash
# Backup nuværende
cd ..
mv "Project 2" "Project 2 backup"

# Opret ny folder
mkdir "Project 2"
cd "Project 2"

# Kopier alle .go filer fra backup
cp "../Project 2 backup"/*.go .
cp "../Project 2 backup"/*.md .

# Init Go module
go mod init logical-clocks

# Test
go run .
```

### Kontakt for Hjælp

Hvis du stadig har problemer:

1. **Check Go version**: `go version` (skal være >= 1.18)
2. **Check file permissions**: `ls -la` (alle filer skal være readable)
3. **Check syntax**: `go build .` (skal ikke give fejl)
4. **Google error message**: Kopier hele error beskeden

### Nyttige Kommandoer

```bash
# Se Go environment
go env

# Ryd build cache
go clean -cache

# Format kode (gør den pæn)
go fmt *.go

# Vet kode (find potentielle bugs)
go vet

# Liste dependencies
go list -m all

# Se hvorfor en package bruges
go mod why [package]
```

## ✅ Success Checklist

Når alt virker, skulle du kunne:

- [ ] Køre `go version` og se Go version
- [ ] Køre `go run .` og se simulation output
- [ ] Køre `go test` og se "PASS"
- [ ] Køre `go test -bench=.` og se benchmarks
- [ ] Forstå output fra programmet
- [ ] Modificere koden og køre igen

**Hvis du kan check alle disse, er du klar til at arbejde med projektet! 🎉**

---

## 💡 Pro Tips

### Brug VS Code

Hvis du bruger VS Code:

1. Installér Go extension:
   ```
   Command Palette (⌘+Shift+P) → "Install Extensions" → "Go"
   ```

2. Auto-format on save:
   ```json
   // settings.json
   "[go]": {
       "editor.formatOnSave": true
   }
   ```

3. Test explorer:
   - Go-ikonet i sidebar viser alle tests
   - Klik for at køre individual tests

### Brug Git

Hvis du vil tracke ændringer:

```bash
cd "Project 2"
git init
git add .
git commit -m "Initial implementation of logical clocks"
```

### Dokumenter Ændringer

Hvis du modificerer koden:

```bash
# Før ændringer
git commit -am "Before modifying X"

# Efter ændringer
git commit -am "Modified X to do Y"

# Se ændringer
git diff HEAD~1
```

---

**God fornøjelse! Du har nu alt du skal bruge til at forstå og køre projektet. 🚀**
