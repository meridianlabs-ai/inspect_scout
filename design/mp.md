# Multi-Process Concurrency Architecture

## Overview

The multi-process concurrency strategy distributes scanner work across multiple worker processes, each running its own async event loop with multiple concurrent tasks. This provides true CPU parallelism while maintaining high I/O concurrency within each process.

**Key characteristics:**
- Fork-based process creation for efficient state sharing
- Nested concurrency: N processes × M async tasks = N×M total concurrency
- Queue-based IPC for work distribution and result collection
- Robust shutdown handling for both normal and interrupted execution

## Process Creation via Fork

### Fork Mechanism

The architecture uses Python's `fork` multiprocessing context to create worker processes:

```python
ctx = multiprocessing.get_context("fork")
p = ctx.Process(target=subprocess_main, args=(worker_id,))
```

Fork creates a new process by duplicating the parent process's memory space. The child process starts with an identical copy of the parent's memory, including:
- Global variables
- Imported modules
- Function definitions
- Data structures

### Copy-on-Write Semantics

Fork uses copy-on-write (CoW) memory management:
- Initially, child processes share the parent's memory pages (read-only)
- Only when a process modifies memory does the OS create a private copy of that page
- Read-only data (functions, shared context) stays shared across all processes

**Benefits:**
- **Fast process creation**: No need to pickle/unpickle complex objects
- **Memory efficient**: Shared read-only data (code, immutable config) uses no extra memory
- **Simple state sharing**: Workers inherit parent state automatically

**Why this works for us:**
- Parse and scan functions are read-only (workers never modify them)
- Configuration (task counts, diagnostics flags) is read-only
- Queues and synchronization primitives work across process boundaries

## IPC Mechanisms

The architecture uses three IPC mechanisms: a read only context implicitly shared by the fork, `multiprocessing.Queue`'s for data flow, and a `multiprocessing.Condition` variable for shutdown signaling.

### Shared Context (IPCContext)

**File:** `_mp_common.py`

The `IPCContext` dataclass contains all read-only configuration state shared between the main process and workers:

```python
@dataclass
class IPCContext:
    parse_function: Callable[[ParseJob], Awaitable[list[ScannerJob]]]
    scan_function: Callable[[ScannerJob], Awaitable[list[ResultReport]]]
    tasks_per_process: int
    prefetch_multiple: float | None
    diagnostics: bool
    overall_start_time: float
    parse_job_queue: MPQueue[ParseJob | None]
    upstream_queue: MPQueue[UpstreamQueueItem]
    shutdown_condition: MPCondition
```

**Sharing mechanism:**
- Stored as a module-level global: `ipc_context = cast(IPCContext, None)`
- Main process initializes it before forking
- Workers inherit it via fork (no serialization needed)
- **Never mutated** - all fields are read-only after initialization

**Why module-level?**
- Fork duplicates the parent's entire memory space, including module globals
- Workers access the same `_mp_common.ipc_context` variable
- No need to pass context as arguments or pickle complex objects
- No need to worry about synchronization - it's immutable

### Multiprocessing Queues

Two unbounded queues handle data flow between processes:

#### 1. parse_job_queue
- **Direction:** Main → Workers
- **Contents:** ParseJob objects (lightweight metadata: transcript info, scanner indices)
- **Producer:** Main process's `_producer()` task
- **Consumers:** Worker processes
- **Sentinel:** `None` (signals workers to stop, one per task)

**Why unbounded:**
ParseJobs are tiny metadata objects. Real backpressure happens inside workers via the single-process strategy's scanner job buffer.

#### 2. upstream_queue
- **Direction:** Workers → Main
- **Contents:** Multiplexed stream of:
  - Scan results: `(TranscriptInfo, scanner_name, results)` - 3-tuple
  - Worker metrics: `(worker_id, ScanMetrics)` - 2-tuple
  - Exceptions: `Exception` instances
  - Completion: `None`
- **Producers:** Worker processes
- **Consumer:** Main process's `_upstream_collector()` task
- **Sentinels:**
  - `None` from workers (clean completion, one per worker)
  - `_SHUTDOWN_SENTINEL` from main process (Ctrl-C shutdown)

**Message discrimination:**
The collector distinguishes message types by tuple length (2 vs 3 elements) and `isinstance` checks.

**Queue operations and async integration:**
- `queue.get()` is blocking with no async support
- Use `anyio.to_thread.run_sync(queue.get)` to avoid blocking the event loop
- `queue.put()` on unbounded queues only blocks briefly for lock contention (no threading needed)

### Shutdown Condition

**Type:** `multiprocessing.Condition`

**Purpose:** Allows main process to signal all workers to shut down simultaneously during Ctrl-C.

**Mechanism:**
- Each worker runs a shutdown monitor task that waits on the condition
- Main process signals the condition during shutdown: `shutdown_condition.notify_all()`
- Workers wake up and cancel their work tasks

**Why needed:**
- Provides immediate shutdown response (<10ms typical)
- More reliable than terminate/kill alone
- Allows workers to handle cancellation cleanly before forced termination

## Architecture Components

### Main Process

The main process orchestrates work distribution, result collection, and worker lifecycle.

**File:** `multi_process.py`

**Roles:**

1. **Producer Task (`_producer`)**
   - Reads ParseJobs from input iterator
   - Puts them on `parse_job_queue`
   - Sends `None` sentinels when done (one per worker task)

2. **Upstream Collector Task (`_upstream_collector`)**
   - Reads from `upstream_queue` (multiplexed stream)
   - Discriminates message types by tuple length and `isinstance`
   - For results (3-tuple): calls `record_results()`
   - For metrics (2-tuple): aggregates and updates display
   - For exceptions: re-raises them
   - Counts worker completion via `None` sentinels
   - Exits on `_SHUTDOWN_SENTINEL` (Ctrl-C path)

3. **Process Manager**
   - Spawns worker processes via fork
   - Manages signal handlers (SIGINT)
   - Executes shutdown sequence

**Task group structure:**
Both tasks run in a single `anyio.create_task_group()`, sharing a cancel scope. This enables:
- Coordinated cancellation on Ctrl-C
- Automatic cleanup when any task fails
- Clean completion when all tasks finish

### Worker Process

Each worker runs independently with its own event loop and internal concurrency.

**File:** `_mp_subprocess.py`

**Structure:**

```
subprocess_main(worker_id)
  └─ anyio.run(_worker_main)
      └─ anyio.create_task_group()
          ├─ shutdown_monitor_task (monitors shutdown_condition)
          └─ work_task (runs single_process_strategy)
```

**Components:**

1. **Shutdown Monitor Task (`_shutdown_monitor_task`)**
   - Runs in its own cancel scope (can be cancelled independently)
   - Blocks on `shutdown_condition.wait()` in a thread
   - When signaled: cancels the entire task group's work
   - When work completes: cancelled by work task to allow task group to exit

2. **Work Task (`_work_task`)**
   - Runs `single_process_strategy` with local concurrency
   - Reads ParseJobs from `parse_job_queue`
   - Sends both results and metrics to `upstream_queue`
   - In `finally` block: cancels shutdown monitor to prevent hang

**Critical design detail:**
The shutdown monitor must be cancelled when work completes, otherwise it blocks indefinitely on `condition.wait()`, preventing the task group from exiting and the completion sentinel from being sent.

## Shutdown Flows

### Normal Completion Flow

**Sequence:**

1. **Producer completes**
   - Input iterator exhausted
   - Sends `None` sentinels to parse_job_queue (one per worker task)
   - Producer task exits

2. **Workers complete**
   - Each worker task processes its sentinel (`None`)
   - Single-process strategy completes normally
   - Work task's `finally` block cancels shutdown monitor
   - Task group exits (both tasks done)
   - `else:` clause executes: sends single `None` sentinel to upstream_queue
   - Worker process exits

3. **Collector completes**
   - Upstream collector receives `None` from each worker (counts completions)
   - Collector exits when all workers accounted for
   - Task group exits normally

4. **Cleanup**
   - `finally` block runs shutdown sequence
   - Processes already dead (Phase 1-4 skip)
   - Queues drained and closed (Phase 6-9)

**Timeline:**
```
Producer: [running...] → Done → Exit
Worker 0: [running...] → Done → Send sentinel → Exit
Worker 1: [running...] → Done → Send sentinel → Exit
Collector: [waiting...] → Got 2/2 → Exit
Main: All tasks complete → Cleanup → Done
```

### Ctrl-C Shutdown Flow

**Sequence:**

1. **User presses Ctrl-C**
   - SIGINT delivered to process group
   - Workers immune (SIGINT = SIG_IGN)
   - Only parent receives signal

2. **KeyboardInterrupt raised**
   - Raised in main process's task group
   - All tasks (producer, collector) cancelled
   - Producer's `finally` block still sends `None` sentinels (shield)
   - Collector's thread blocked on `queue.get()` - doesn't respond to cancellation

3. **Shutdown sequence begins (in `finally` block)**

   **Phase 1: Signal workers**
   ```python
   with shutdown_condition:
       shutdown_condition.notify_all()
   ```
   - Wakes all shutdown monitor tasks
   - Monitors cancel their work tasks
   - Workers handle cancellation (no sentinels sent)

   **Phase 2: Graceful wait (2 seconds)**
   - Wait for workers to exit cleanly
   - Most workers exit within milliseconds

   **Phase 3: Terminate stragglers**
   - Send SIGTERM to any still-alive workers
   - Wait 1 more second

   **Phase 4: Force kill survivors**
   - Send SIGKILL to any survivors (rare)
   - Immediate termination

   **Phase 5: Inject shutdown sentinel**
   - Put `_SHUTDOWN_SENTINEL` into upstream_queue
   - Wakes collector's blocked `queue.get()` thread
   - Collector detects sentinel and exits immediately

   **Phase 6: Drain queues**
   - Remove any remaining items (orphaned results)
   - Prevents blocking on queue cleanup

   **Phase 7: Close queues**
   - Send sentinel to internal feeder threads
   - Signals queues to stop accepting data

   **Phase 8-9: Cleanup threads**
   - Wait for feeder threads to exit
   - Cancel join threads as last resort

**Timeline:**
```
User: Ctrl-C
Main: KeyboardInterrupt → Cancel all tasks → finally
Workers: [running...] → Signaled → Cancelled → Exit (or terminated)
Collector: [blocked on queue.get()...] → Sentinel injected → Exit
Main: All processes dead → Queues cleaned → Done
```

**Key design: Why inject shutdown sentinel?**

During Ctrl-C, workers are terminated before they can send their normal `None` sentinels. The collector is blocked on `queue.get()` in a thread, waiting for completions that will never arrive.

Without the shutdown sentinel injection:
- Collector would block forever
- Main process couldn't exit
- User would need to force-kill

With the shutdown sentinel:
- Main process injects `_SHUTDOWN_SENTINEL` into upstream_queue
- Wakes blocked collector thread
- Collector immediately exits
- Clean shutdown completes in <1 second

## Key Design Decisions

### Signal Handling Strategy

**Problem:** During Ctrl-C, SIGINT is delivered to all processes in the group. Without coordination, each process tries to handle shutdown independently, causing races and hangs.

**Solution:** Workers ignore SIGINT, only parent responds.

**Implementation:**
```python
# Before fork: block SIGINT, workers inherit SIG_IGN
original_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

# Fork workers (they inherit blocked signal)
processes = [ctx.Process(...) for _ in range(count)]

# After fork: restore handler in parent only
signal.signal(signal.SIGINT, original_handler)
```

**Benefits:**
- Only one process (parent) handles KeyboardInterrupt
- Parent has full control over shutdown sequence
- Workers don't race or interfere
- Predictable, testable shutdown behavior

### Sentinel Pattern for Coordination

**Problem:** How do async tasks know when to stop reading from queues?

**Solution:** Send special sentinel values through queues.

**Two types:**

1. **Worker completion sentinels (`None`)**
   - Sent by workers when they finish normally (one per worker)
   - Collector counts these to know when all workers are done
   - Type: `None` (simple, unambiguous)

2. **Shutdown sentinels (`_SHUTDOWN_SENTINEL = object()`)**
   - Sent by main process during Ctrl-C
   - Wakes blocked collector immediately
   - Type: `object()` with unique identity (can't be forged)

**Why `object()` for shutdown sentinel?**
- Unique identity: `sentinel is _SHUTDOWN_SENTINEL` (not just `==`)
- Can't be created by user code
- Can't collide with legitimate data
- Works with any queue type (no type constraints)

### Shutdown Monitor Architecture

**Problem:** During Ctrl-C, workers need to respond quickly, but they're busy processing work in async tasks. How to interrupt them?

**Solution:** Dedicated shutdown monitor task that waits on a condition variable.

**Architecture:**
```python
async with anyio.create_task_group() as tg:
    # Monitor in its own cancel scope
    tg.start_soon(monitor_wrapper)

    # Work task
    tg.start_soon(work_task)
```

**Monitor behavior:**
- Blocks on `condition.wait()` in a thread
- When signaled: cancels entire task group
- When work finishes: gets cancelled to allow exit

**Benefits:**
- **Fast response:** Workers shutdown in <10ms typically
- **Clean cancellation:** Work tasks handle cancellation properly
- **No polling:** Condition variable is efficient (kernel sleep)
- **Prevents hang:** Monitor must be cancelled on completion

**Critical detail:**
The monitor must be cancelled when work completes, otherwise:
1. Work task finishes
2. Monitor still blocks on `condition.wait()`
3. Task group waits forever for monitor
4. Sentinel never sent
5. Collector hangs → entire program hangs

This was a bug that was recently fixed - see the comments in `_mp_subprocess.py`.

## File Map

- `multi_process.py` - Main process orchestration, producer, upstream collector
- `_mp_subprocess.py` - Worker process entry point, shutdown monitor
- `_mp_common.py` - Shared IPC context and types
- `_mp_shutdown.py` - Unified shutdown sequence (9 phases)
- `_iterator.py` - Async iterators for queue consumption
- `single_process.py` - Nested async concurrency within workers
