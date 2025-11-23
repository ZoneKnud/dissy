=================================================
   DISTRIBUTED SYSTEMS - LOGICAL CLOCKS PROJECT
   Lamport Timestamps vs Vector Clocks
=================================================


### DEMO 1: LAMPORT CLOCK SIMULATION ###

=== Running Scenario ===
Phase 1: Initial local events (processer arbejder uafhængigt)
Phase 2: Communication starts

=== Event Logs ===

Process 0:
  P0: Local event T1: Initialize P0
  P0: Local event T2: Event A
  P0: Send to P1 at T3: Message from P0
  P0: Receive from P2 (received T9, was T3 → synchronized to T10): Message from P2
  P0: Local event T11: Event D

Process 1:
  P1: Local event T1: Initialize P1
  P1: Local event T2: P1 local work
  P1: Receive from P0 (received T3, was T2 → synchronized to T4): Message from P0
  P1: Local event T5: Event B
  P1: Send to P2 at T6: Message from P1

Process 2:
  P2: Local event T1: Initialize P2
  P2: Local event T2: P2 local work
  P2: Receive from P1 (received T6, was T2 → synchronized to T7): Message from P1
  P2: Local event T8: Event C
  P2: Send to P0 at T9: Message from P2
  P2: Local event T10: Event E


### DEMO 2: VECTOR CLOCK SIMULATION ###

=== Running Scenario ===
Phase 1: Initial local events (processer arbejder uafhængigt)
Phase 2: Communication starts

=== Event Logs ===

Process 0:
  P0: Local event [1,0,0] at Initialize P0
  P0: Local event [2,0,0] at Event A
  P0: Send to P1 at [3,0,0]: Message from P0
  P0: Receive from P2 (received [3,5,5], was [3,0,0] → synchronized to [4,5,5]): Message from P2
  P0: Local event [5,5,5] at Event D

Process 1:
  P1: Local event [0,1,0] at Initialize P1
  P1: Local event [0,2,0] at P1 local work
  P1: Receive from P0 (received [3,0,0], was [0,2,0] → synchronized to [3,3,0]): Message from P0
  P1: Local event [3,4,0] at Event B
  P1: Send to P2 at [3,5,0]: Message from P1

Process 2:
  P2: Local event [0,0,1] at Initialize P2
  P2: Local event [0,0,2] at P2 local work
  P2: Receive from P1 (received [3,5,0], was [0,0,2] → synchronized to [3,5,3]): Message from P1
  P2: Local event [3,5,4] at Event C
  P2: Send to P0 at [3,5,5]: Message from P2
  P2: Local event [3,5,6] at Event E


=== CONCURRENCY DETECTION DEMO ===
This demonstrates the key difference between Lamport and Vector clocks

Scenario: P0 and P2 have concurrent events

Lamport Clock Result:
  P0 time: 1
  P2 time: 1
  → Lamport kan IKKE detektere at disse er concurrent
  → Den kan kun sige at P0's event har lavere timestamp

Vector Clock Result:
  P0 vector: [1,0,0]
  P2 vector: [0,0,1]
  → Vector clock KAN detektere at disse er concurrent!
  → Ingen causal relationship mellem dem


### DEMO 3: PERFORMANCE BENCHMARK ###

=== Running Benchmark ===
Processes: 5, Events per process: 10

Testing Lamport Clock...
Testing Vector Clock...


=== COMPARISON ===

--- Lamport Metrics ---
Processes:           5
Total Events:        50
Execution Time:      122.812167ms
Memory Used:         60544 bytes (59.12 KB)
Message Overhead:    8 bytes per message
Ordering Capability: 75.0%

--- Vector Metrics ---
Processes:           5
Total Events:        50
Execution Time:      121.992375ms
Memory Used:         87920 bytes (85.86 KB)
Message Overhead:    40 bytes per message
Ordering Capability: 100.0%

--- Analysis ---
Time Overhead (Vector vs Lamport): -819.792µs (-0.7%)
Memory Overhead (Vector vs Lamport): +27376 bytes (+45.2%)
Message Size Overhead (Vector vs Lamport): +32 bytes (+400.0%)
Ordering Capability Improvement: +25.0%

--- Summary ---
Lamport Clock:
  + Lower time overhead
  + Lower memory usage
  + Smaller message size
  - Only partial ordering (cannot determine order of concurrent events)

Vector Clock:
  + Total ordering capability (can determine all causal relationships)
  + Can detect concurrent events
  - Higher overhead (time, space, message size)
  - Overhead scales with number of processes (O(n) per message)

Recommendation:
- Use Lamport if you only need to know 'happened before' relationships
- Use Vector if you need to detect concurrency or need total ordering


### DEMO 4: SCALABILITY TEST ###
Testing with more processes to show overhead scaling...

=== Running Benchmark ===
Processes: 10, Events per process: 10

Testing Lamport Clock...
Testing Vector Clock...


=== COMPARISON ===

--- Lamport Metrics ---
Processes:           10
Total Events:        100
Execution Time:      122.705417ms
Memory Used:         112000 bytes (109.38 KB)
Message Overhead:    8 bytes per message
Ordering Capability: 75.0%

--- Vector Metrics ---
Processes:           10
Total Events:        100
Execution Time:      123.249625ms
Memory Used:         254400 bytes (248.44 KB)
Message Overhead:    80 bytes per message
Ordering Capability: 100.0%

--- Analysis ---
Time Overhead (Vector vs Lamport): 544.208µs (+0.4%)
Memory Overhead (Vector vs Lamport): +142400 bytes (+127.1%)
Message Size Overhead (Vector vs Lamport): +72 bytes (+900.0%)
Ordering Capability Improvement: +25.0%

--- Summary ---
Lamport Clock:
  + Lower time overhead
  + Lower memory usage
  + Smaller message size
  - Only partial ordering (cannot determine order of concurrent events)

Vector Clock:
  + Total ordering capability (can determine all causal relationships)
  + Can detect concurrent events
  - Higher overhead (time, space, message size)
  - Overhead scales with number of processes (O(n) per message)

Recommendation:
- Use Lamport if you only need to know 'happened before' relationships
- Use Vector if you need to detect concurrency or need total ordering


=================================================
   SIMULATION COMPLETE
=================================================