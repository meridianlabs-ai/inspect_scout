# Exception Handling Architecture

## Overview

The scanner execution system distinguishes between two fundamentally different categories of exceptions, each with distinct handling strategies:

1. **Job Exceptions**: Failures during the execution of individual parse or scan operations
2. **Infrastructure Exceptions**: Failures in the concurrency control machinery itself

This separation ensures that individual work item failures don't crash the entire scan, while genuine system-level problems are properly propagated and handled.

## Job Exception Handling

### Responsibility Boundary

**Job exceptions** occur during the execution of user-provided scanner code or data processing operations. These are expected and recoverable - they represent failures of individual work items, not the scanning system itself.

**Examples:**
- Scanner function throws an error
- Model API call fails or times out
- Loader encounters malformed data
- Type errors in scanner input processing
- User code accessing undefined attributes

### Containment Strategy

Two functions serve as the **containment boundary** for job exceptions:

1. **`_parse_function`**: Executes parse jobs (transcript reading and scanner job creation)
2. **`_scan_function`**: Executes scan jobs (running scanner functions on inputs)

**Design Principle:** Both functions must catch ALL exceptions from their operations. Exceptions are transformed into `Error` objects within `ResultReport` structures. **No exceptions should escape these functions** - they always return normally, possibly with Error results.

This ensures:
- The scan can continue processing other work items
- Failures are recorded and reportable in scan results
- The concurrency machinery remains unaffected by user code failures

### Error Transformation

When a job exception occurs:
1. Exception is caught at the function boundary
2. Exception details (message, traceback) are captured
3. An `Error` object is created with the exception information
4. The Error is embedded in the `ResultReport` for that work item
5. Function returns normally with the Error result

The scan recorder persists these Error results, making failures visible in scan output and enabling post-scan analysis of what went wrong.

## Infrastructure Exception Handling

### Definition

**Infrastructure exceptions** occur in the scan process coordination, concurrency control machinery, or IPC mechanisms. These are unexpected and unrecoverable - they represent system-level failures that prevent the scan from continuing correctly.

**Examples:**
- Queue operation failures
- Process spawn or fork failures
- IPC communication errors (manager proxy failures)
- Event loop corruption
- Worker process crashes
- Resource exhaustion (memory, file descriptors)
- Semaphore registry coordination failures

### Propagation Strategy

Infrastructure exceptions must propagate to the top level to terminate the scan with a clear error. However, in a multi-process architecture, this propagation requires careful coordination.

**Design Principle:** Infrastructure exceptions use a **single communication path** from worker to parent - the upstream queue. Workers do NOT use exception bubble-up (re-raising) because the parent doesn't monitor worker process exit codes.

## Multi-Process Exception Flow

### Worker Exception Handling

When a worker encounters an infrastructure exception:

1. **Catch**: Worker's exception handler catches the exception
2. **Report**: Worker sends the exception object to parent via `upstream_queue.put(exception)`
3. **Exit Gracefully**: Worker exits cleanly (possibly sending `WorkerComplete` sentinel first, or simply returning)
4. **No Re-raise**: Worker does NOT re-raise the exception

The graceful exit ensures the worker doesn't leave the collector hanging. Whether to send `WorkerComplete` before exiting is a design decision - sending it maintains the normal completion contract, but the exception itself signals abnormal termination.

### Parent Exception Handling

When the parent's collector receives an infrastructure exception from the queue:

1. **Match**: Pattern matching identifies the item as an `Exception` instance
2. **Propagate**: Exception is re-raised in the collector task
3. **Cancel**: Task group catches the exception, cancelling the producer task
4. **Shutdown**: Exception propagates to the strategy's exception handler
5. **Cleanup**: Shutdown machinery terminates remaining workers, drains queues, cleans up resources

This ensures orderly teardown even when one worker encounters an infrastructure failure.

