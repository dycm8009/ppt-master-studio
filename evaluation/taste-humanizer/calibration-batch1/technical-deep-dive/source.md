# Per-thread arenas in the Atlas C++ event pipeline

> Closed evaluation fixture. Atlas is a fictional internal service. Treat every value and technical statement below as authoritative for this evaluation. Do not add benchmarks, hardware claims, or causal explanations that are not stated here.

## System context

Atlas is a C++20 event-processing service running on Linux. One production instance has 16 worker threads and processes an average of 80,000 events per second. Events arrive in batches of up to 512.

Each event passes through parsing, validation, enrichment, and serialization. Before the change, intermediate objects used the general-purpose allocator.

## Baseline

A seven-day production sample showed:

| Metric | Baseline |
|---|---:|
| p50 end-to-end latency | 7.4 ms |
| p99 end-to-end latency | 63 ms |
| Heap allocations | 2.8 million/s |
| Resident set size | 9.1 GiB |
| Allocation-related CPU samples | 18% |

The profile showed allocation and deallocation work across all four pipeline stages. The sample establishes correlation, not proof that allocation was the only source of tail latency.

## Design

The change introduces one monotonic arena per worker thread and per active batch.

- The worker creates or reuses an arena when it starts a batch.
- Parsing, validation, and enrichment allocate short-lived objects from that arena.
- Serialization writes into an output buffer owned by the batch.
- The arena resets only after every event in the batch has completed serialization.
- Objects that cross a worker-thread boundary must be immutable and use ordinary ownership outside the arena.
- Any single request larger than 64 KiB uses the fallback allocator.
- The arena's retained capacity is capped at 32 MiB per worker.
- A high-water metric records retained bytes before each reset.

The design does not replace the allocator for long-lived caches, shared state, logging buffers, or network I/O.

## Safety incident in staging

The first staging build reset the arena when enrichment completed. Serialization still held string views into arena memory. This caused one reproducible crash in a 40-minute stress test.

The fix moved reset ownership to the batch completion barrier. The code now rejects arena-backed types from the cross-thread handoff interface at compile time through a constrained wrapper type.

Do not hide this failure. It is the main reason the rollout includes extra guards.

## Result

A second seven-day sample on the same production fleet showed:

| Metric | Baseline | Arena build |
|---|---:|---:|
| p50 latency | 7.4 ms | 5.9 ms |
| p99 latency | 63 ms | 28 ms |
| Heap allocations | 2.8 million/s | 0.42 million/s |
| Resident set size | 9.1 GiB | 10.1 GiB |
| Allocation-related CPU samples | 18% | 6% |

The arena build reduced allocation activity and latency in this workload while increasing resident memory by 1.0 GiB, about 11%. The test does not establish that the same trade-off applies to other services.

## Rollout proposal

Ship to 10% of production instances for 72 hours with these automatic rollback conditions:

- p99 latency above 50 ms for 15 minutes;
- resident set size above 11.5 GiB;
- any arena lifetime assertion failure;
- any increase in process crash rate.

Expand to 50% only after the 72-hour window passes and a manual review confirms no lifetime violations. Full rollout requires a second review.

## Required close

The decision is whether to approve the guarded 10% rollout. The presentation must explain the lifecycle, the staging failure, the measured trade-off, and the rollback conditions before making the ask.
