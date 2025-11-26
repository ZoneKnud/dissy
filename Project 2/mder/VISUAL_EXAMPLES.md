# Visual Examples - Lamport vs Vector Clocks

## Example 1: Simple Message Exchange

### Scenario
Three processes (P0, P1, P2) communicate with each other.

```
Time flows downward ↓

P0          P1          P2
│           │           │
├─ A (1)    │           │         P0: Local event A
│           │           │
├─ send ──→ ├─ B (2)    │         P0 sends to P1 (T=2)
│           │           │         P1 receives (T=2), happens event B (T=3)
│           ├─ send ──→ ├─ C (4)  P1 sends to P2 (T=3)
│           │           │         P2 receives (T=3), happens event C (T=4)
├─ D (3)    │           │         P0: Local event D (concurrent with C!)
│           │           │
```

### Lamport Timestamps

```
P0: A=1, send=2, D=3
P1: receive=3, B=3, send=4
P2: receive=5, C=5

Timeline: A(1) < send(2) < D(3) < receive(3) < B(3) < send(4) < receive(5) < C(5)

Problem: D(3) < B(3) suggests D happened before B, 
         but they are actually concurrent!
```

**Lamport kan IKKE detektere at D og B er concurrent!**

### Vector Clocks

```
P0: A=[1,0,0], send=[2,0,0], D=[3,0,0]
P1: receive=[2,1,0], B=[2,1,0], send=[2,2,0]
P2: receive=[2,2,1], C=[2,2,1]

Compare D=[3,0,0] and B=[2,1,0]:
  - Position 0: 3 > 2  ← P0 is ahead
  - Position 1: 0 < 1  ← P1 is ahead
  → They are CONCURRENT! Neither happened before the other.
```

**Vector clocks KAN detektere concurrency!**

---

## Example 2: Fork-Join Pattern

### Scenario
P0 broadcasts to P1 and P2, then they both send back to P0.

```
         P0
        ╱  ╲
      ╱      ╲
    P1        P2
      ╲      ╱
        ╲  ╱
         P0
```

### Lamport Timestamps

```
P0: broadcast_1=1, broadcast_2=2, receive_1=?, receive_2=?
P1: receive=3, send=4
P2: receive=3, send=4

P0: receive_1=5, receive_2=6

Timeline: 1 < 2 < 3 < 4 < 5 < 6

Problem: We can't tell that P1's send(4) and P2's send(4) 
         are concurrent!
```

### Vector Clocks

```
P0: broadcast_1=[1,0,0], broadcast_2=[2,0,0]
P1: receive=[2,1,0], send=[2,2,0]
P2: receive=[2,0,1], send=[2,0,2]

P0: receive_1=[2,2,1], receive_2=[2,2,2]

Compare P1's send=[2,2,0] and P2's send=[2,0,2]:
  - Position 0: 2 = 2  ✓
  - Position 1: 2 > 0  ← P1 is ahead
  - Position 2: 0 < 2  ← P2 is ahead
  → CONCURRENT!
```

---

## Example 3: Causality Violation Detection

### Scenario
Can we detect if messages arrive out of order?

```
P0: send msg1 (content: "Hello")
P0: send msg2 (content: "How are you?")

P1 receives: msg2 first, then msg1  ← Out of order!
```

### Lamport Timestamps

```
P0: send1=1, send2=2
P1: receives msg2 (T=2) → updates to T=3
P1: receives msg1 (T=1) → updates to max(3,1)+1 = 4

P1 accepts both messages but has no way to detect the ordering violation!
```

### Vector Clocks

```
P0: send1=[1,0], send2=[2,0]
P1: initial=[0,0]

P1 receives msg2=[2,0] first:
  P1: merge [0,0] and [2,0] → [2,1]
  
P1 receives msg1=[1,0]:
  P1: merge [2,1] and [1,0] → [2,2]
  
Compare msg1=[1,0] and msg2=[2,0]:
  msg1 < msg2  (msg1 happened before msg2)
  
P1 can detect that msg1 should have come first!
```

**Vector clocks enable causal delivery protocols!**

---

## Example 4: Scaling Overhead

### Scenario
How does overhead scale with number of processes?

```
Number of processes: 2, 5, 10, 50, 100

Lamport: Message size = 8 bytes (1 int)
Vector:  Message size = 8 * n bytes (n ints)
```

| Processes | Lamport | Vector  | Overhead Ratio |
|-----------|---------|---------|----------------|
| 2         | 8 B     | 16 B    | 2x             |
| 5         | 8 B     | 40 B    | 5x             |
| 10        | 8 B     | 80 B    | 10x            |
| 50        | 8 B     | 400 B   | 50x            |
| 100       | 8 B     | 800 B   | 100x           |

**Observation:** Vector clock overhead is O(n) per message!

This is why modern systems use:
- **Dotted Version Vectors**: Optimization that only sends relevant entries
- **Interval Tree Clocks**: Dynamic growth, only O(log n) overhead
- **Hybrid Logical Clocks**: Combines physical time with logical

---

## Example 5: Concurrent Events Frequency

### Scenario
In a real system, how often are events truly concurrent?

```
System: 10 processes, each sending 100 messages randomly

Lamport cannot distinguish: ~60% of event pairs
Vector can distinguish:      100% of event pairs

Why ~60%?
- Many events in distributed systems ARE concurrent
- Network delays create natural concurrency
- Lamport treats all events with different timestamps as ordered
  (even when they're actually concurrent)
```

**Real-world impact:**
- **Banking**: Concurrent transactions on same account → need detection
- **Collaborative editing**: Concurrent edits → need conflict resolution
- **Distributed databases**: Concurrent writes → need to merge or reject

---

## Visualization Symbols Used

```
│   Process timeline (time flows downward)
├─  Event happening in process
─→  Message being sent
(n) Lamport timestamp
[a,b,c] Vector clock
||  Concurrent events
<   Happened-before relation
```

---

## Summary Table

| Feature | Lamport | Vector |
|---------|---------|--------|
| **Can detect A → B** | ✅ Yes | ✅ Yes |
| **Can detect A ∥ B** | ❌ No | ✅ Yes |
| **Message size** | O(1) | O(n) |
| **Memory per process** | O(1) | O(n) |
| **Update time** | O(1) | O(n) |
| **Compare time** | O(1) | O(n) |
| **Best for** | Simple ordering | Full causality |

Where:
- A → B means "A happened before B"
- A ∥ B means "A and B are concurrent"
- n = number of processes

---

## When to Use What?

### Use Lamport when:
✅ You only need to timestamp events for ordering  
✅ You have many processes (>100)  
✅ Message size matters  
✅ You don't need to detect concurrency  

**Examples:**
- Log file merging
- Event ordering in monitoring systems
- Simple distributed debugging

### Use Vector when:
✅ You need to detect concurrent operations  
✅ You need causal consistency  
✅ Number of processes is moderate (<50)  
✅ Correctness is more important than efficiency  

**Examples:**
- Distributed databases (conflict detection)
- Collaborative editing (operational transformation)
- Distributed version control
- Causal message delivery

### Use Modern Alternatives when:
✅ You need vector clock benefits but better scalability  
✅ Processes can join/leave dynamically  
✅ You can use physical time with bounded uncertainty  

**Examples:**
- Google Spanner (TrueTime + logical)
- CRDTs with Dotted Version Vectors
- Systems with GPS/atomic clocks
