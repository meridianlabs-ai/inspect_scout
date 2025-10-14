# Multi-Process Concurrency Architecture

## Overview

The multi-process concurrency strategy distributes scanner work across multiple worker processes, each running its own async event loop with multiple concurrent tasks. This provides true CPU parallelism while maintaining high I/O concurrency within each process.

**Key characteristics:**
- Fork-based process creation for efficient state sharing
- Nested concurrency: N processes × M async tasks = N×M total concurrency
- Queue-based IPC for work distribution and result collection
- Robust shutdown handling for both normal and interrupted execution

## Process Creation via Fork

The architecture uses Python's `fork` multiprocessing context to create worker processes. Fork duplicates the parent's memory space, allowing workers to inherit the shared `IPCContext` (including parse/scan functions, configuration, and IPC primitives) without serialization. Copy-on-write semantics make this fast and memory-efficient, since read-only data remains shared across all processes.

## IPC Mechanisms

The architecture coordinates processes through three mechanisms (see `_mp_common.py`):

### 1. Shared Context (IPCContext)
A module-level global containing immutable configuration (parse/scan functions, task counts, IPC primitives, semaphore registry). Initialized before forking, inherited by workers via copy-on-write. Never mutated after initialization.

### 2. Multiprocessing Queues
Two unbounded queues handle data flow:
- **parse_job_queue** (Main → Workers): Lightweight ParseJob metadata with `None` sentinels for completion
- **upstream_queue** (Workers → Main): Multiplexed stream of results, metrics, semaphore requests, and control messages (using strongly-typed dataclasses: `ResultItem`, `MetricsItem`, `SemaphoreRequest`, `WorkerComplete`, `ShutdownSentinel`, `Exception`). Main uses pattern matching to discriminate message types.

Queue operations use `anyio.to_thread.run_sync()` for blocking `.get()` calls to avoid blocking the event loop.

### 3. Synchronization Primitives
Both conditions are created via `SyncManager.Condition()` for consistency. Despite the `threading.Condition` type signature, they are cross-process capable proxy objects that coordinate between processes via the manager's server:
- **shutdown_condition**: Allows main process to signal all workers simultaneously during Ctrl-C. Workers run a dedicated monitor task that waits on this condition.
- **semaphore_condition**: Coordinates access to the cross-process semaphore registry, allowing workers to wait efficiently when requesting semaphores from the parent.

## Cross-Process Semaphore Coordination

**Problem:** When scanner code requests concurrency semaphores (e.g., for API rate limiting), workers in separate processes need to coordinate on the same semaphore instance.

**Solution:** A three-tier architecture (see `_mp_registry.py`, `_mp_semaphore.py`):

1. **PicklableMPSemaphore**: Custom semaphore built from SyncManager proxy objects (Value, Condition) that can be stored in a DictProxy. Unlike standard `multiprocessing.Semaphore`, this can be pickled, enabling lazy creation after forking.

2. **Registry implementations**:
   - **ParentSemaphoreRegistry**: Creates `PicklableMPSemaphore` instances in shared DictProxy when requested
   - **ChildSemaphoreRegistry**: Sends `SemaphoreRequest` via upstream_queue, waits on `semaphore_condition` until parent creates it

3. **MPConcurrencySemaphore**: Wraps manager semaphores to provide async `ConcurrencySemaphore` interface (runs blocking acquire/release in threads)

**Flow:** Worker checks local cache → checks shared registry → sends `SemaphoreRequest` → waits on condition → parent creates semaphore in DictProxy → notifies condition → worker retrieves and caches. Subsequent accesses find semaphore directly in shared registry.

Both parent and child call `init_concurrency()` with their respective registries, ensuring transparent use of the appropriate implementation.

## Architecture Components

### Main Process (`multi_process.py`)
Orchestrates work distribution, result collection, and worker lifecycle:
- **Producer task**: Feeds ParseJobs into `parse_job_queue`, sends sentinels when done
- **Collector task**: Reads multiplexed `upstream_queue`, pattern matches on message types (results, metrics, semaphore requests), handles completion sentinels and shutdown signals
- **Process manager**: Spawns workers via fork, manages SIGINT handlers, executes shutdown

Producer and collector run in a single task group, enabling coordinated cancellation on Ctrl-C and automatic cleanup on failures.

### Worker Process (`_mp_subprocess.py`)
Each worker runs its own event loop with two tasks:
- **Shutdown monitor**: Blocks on `shutdown_condition`, cancels work on signal
- **Work task**: Runs `single_process_strategy`, reads from `parse_job_queue`, sends to `upstream_queue`, **must cancel shutdown monitor in `finally` to prevent hang**

Workers initialize `ChildSemaphoreRegistry` to enable cross-process semaphore requests via IPC.

## Shutdown Flows

### Normal Completion
Producer sends sentinels → workers complete and send `WorkerComplete` → collector counts completions and exits → cleanup runs (workers already dead, queues drained/closed).

### Ctrl-C Shutdown
SIGINT delivered only to parent (workers have `SIGINT=SIG_IGN`). Parent's task group cancelled, triggering shutdown sequence (see `_mp_shutdown.py`):

1. **Signal workers**: Notify `shutdown_condition` → shutdown monitors cancel work tasks
2. **Phased termination**: Wait for graceful exit, then SIGTERM stragglers, then SIGKILL survivors
3. **Inject shutdown sentinel**: Put `ShutdownSentinel` into `upstream_queue` to wake collector (workers terminated before sending normal completion sentinels, so collector would block forever otherwise)
4. **Cleanup**: Drain and close queues, wait for feeder threads

**Key design:** Workers ignore SIGINT to avoid races. Parent coordinates shutdown via condition variable + phased process termination. Shutdown sentinel injection prevents collector deadlock when workers are forcibly terminated.

## Key Design Decisions

### Signal Handling
Workers inherit `SIGINT=SIG_IGN` before fork, so only parent receives SIGINT on Ctrl-C. This prevents races and gives parent full control over the shutdown sequence. Parent blocks SIGINT, forks workers, then restores handler.

### Sentinel Pattern
Queue coordination uses strongly-typed dataclass sentinels (`WorkerComplete`, `ShutdownSentinel`) instead of magic values like `None` or `object()`. Provides type safety, works with pattern matching, and self-documents intent.

### Shutdown Monitor
Each worker runs a dedicated monitor task that blocks on `shutdown_condition` in a thread. When signaled, it cancels the work task group for fast shutdown response. **Critical:** The work task must cancel the monitor in its `finally` block, otherwise the monitor blocks forever, preventing the task group from exiting and the completion sentinel from being sent.
