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

**Design Principle:** Ordinary job exceptions become `Error` objects within `ResultReport` by default. `fail_on_error=True`, `PrerequisiteError`, and cancellation bypass this containment and interrupt the scan.

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
- Process spawn failures
- IPC communication errors (manager proxy failures)
- Event loop corruption
- Worker process crashes
- Resource exhaustion (memory, file descriptors)
- Semaphore registry coordination failures

### Propagation Strategy

Infrastructure exceptions must propagate to the top level to terminate the scan with a clear error. However, in a multi-process architecture, this propagation requires careful coordination.

**Design Principle:** Fatal work-task exceptions are reported to the parent through the upstream queue. Workers also re-raise locally; the parent does not use that re-raise to receive the diagnostic.

## Multi-Process Exception Flow

### Worker Exception Handling

When a worker's work task encounters an infrastructure exception, a prerequisite failure, or an explicit fail-fast job error:

1. **Catch**: Worker's exception handler catches the exception
2. **Normalize and report**: Worker sends a `WorkerError` containing worker ID, qualified exception type, message, formatted remote traceback, and optional status/request ID
3. **Re-raise**: The original exception propagates locally; the shutdown monitor is cancelled in `finally`
4. **Completion**: `WorkerComplete` is sent only on clean completion, never to reinterpret a fatal error as success

`WorkerError` contains plain diagnostic strings and an integer worker ID. Optional status/request ID come from the caught exception's own exact built-in `int`/`str` attributes. Exception objects, responses, and traceback locals stay in the worker; exception text itself is not redacted or size-limited.

`TracebackException` formats available chains/groups. If formatting or class metadata fails, the fallback keeps the caught exception's available frames and normalized type/message. The shared single-process strategy selects the exception before this boundary and can already have discarded siblings.

### Parent Exception Handling

When the parent's collector receives an infrastructure exception from the queue:

1. **Match**: Pattern matching identifies `WorkerError`
2. **Propagate**: The collector raises a parent-owned `WorkerProcessError` with the remote diagnostic, without constructing the original provider exception class
3. **Cancel**: Task group catches the exception, cancelling the producer task
4. **Shutdown**: Exception propagates to the strategy's exception handler
5. **Cleanup**: Shutdown machinery terminates remaining workers, drains queues, cleans up resources

This ensures orderly teardown even when one worker encounters an infrastructure failure.

The parent unwraps only single-member task groups and suppresses incidental context. Multi-member groups remain grouped. The public scan path records incomplete status and displays the error. Python 3.10 uses the existing `exceptiongroup` formatter for backported groups; later versions use Rich.

Collector read failures remain fatal. During shutdown, read failures are logged and the affected queue is no longer read, while termination and closure continue. The first read error is raised after teardown only when the scan otherwise completed normally; a primary failure or interruption takes precedence. This includes `ValueError` from a closed queue: the exception type alone does not distinguish closure from failed reconstruction. See [shutdown](mp.md#errors-during-collection-and-shutdown).
