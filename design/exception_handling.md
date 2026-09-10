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

**Design Principle:** Ordinary job exceptions are transformed into `Error` objects within `ResultReport` structures by default. Explicit `fail_on_error=True` and `PrerequisiteError` bypass this containment and interrupt the scan. Cancellation is also allowed to propagate. These exceptions to containment are deliberate; infrastructure failures must not become successful job results.

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

**Design Principle:** Fatal work-task exceptions use the upstream queue to report to the parent. The worker also re-raises locally; its stderr or process exit is not the parent's diagnostic transport. Failures before the worker reaches this work-task boundary retain their existing behavior.

## Multi-Process Exception Flow

### Worker Exception Handling

When a worker's work task encounters an infrastructure exception, a prerequisite failure, or an explicit fail-fast job error:

1. **Catch**: Worker's exception handler catches the exception
2. **Normalize and report**: Worker sends a `WorkerError` containing worker ID, qualified exception type, message, formatted remote traceback, and optional status/request ID
3. **Re-raise**: The original exception propagates locally; the shutdown monitor is cancelled in `finally`
4. **Completion**: `WorkerComplete` is sent only on clean completion, never to reinterpret a fatal error as success

Exception class metadata is guarded too: malformed modules are omitted, and an unreadable type name receives an explicit unavailable marker. In that case, formatting uses the available worker frames and normalized message without consulting the broken class metadata again.

The error payload contains only deliberate scalar fields. It excludes response/request objects, bodies, headers, traceback locals, and exception object graphs. Existing exception text may contain sensitive information; this is not a general redaction guarantee. Other upstream message types retain their existing structures.

Chains and exception groups are preserved as formatted traceback text when they reach this boundary. Optional metadata comes only from the caught exception's own plain `int`/`str` attributes; it is not borrowed from an arbitrary cause or group member. Broken optional getters or formatters do not replace the original diagnostic. The existing single-process strategy still controls which exception reaches the worker boundary.

### Parent Exception Handling

When the parent's collector receives an infrastructure exception from the queue:

1. **Match**: Pattern matching identifies `WorkerError`
2. **Propagate**: The collector raises a parent-owned `WorkerProcessError` with the remote diagnostic, without constructing the original provider exception class
3. **Cancel**: Task group catches the exception, cancelling the producer task
4. **Shutdown**: Exception propagates to the strategy's exception handler
5. **Cleanup**: Shutdown machinery terminates remaining workers, drains queues, cleans up resources

This ensures orderly teardown even when one worker encounters an infrastructure failure.

The parent unwraps only single-member task groups, preserving multi-member groups and avoiding incidental exception context. A failed active collector read remains fatal. The public scan path normally records an incomplete status and displays the fatal error; callers should not depend on catching the original provider class across a process boundary. Single-process handling and default job-error recording remain unchanged.

Python 3.10 uses the existing `exceptiongroup` backport to render task-group failures as text: Rich does not expand those backported groups. This preserves all nested diagnostics at the final display boundary without changing exception propagation. Python 3.11 and later retain Rich's native group rendering.

Both shutdown drains log unexpected read failures through a module logger, stop reading the affected queue, and continue bounded termination and queue closure. A consumed item's decoding failure does not prove that its pipe is healthy. Shutdown returns its first read error after teardown; the parent raises it only after otherwise normal completion. An existing primary error, cancellation, or swallowed `KeyboardInterrupt` takes precedence. Other unexpected cleanup exceptions are also secondary when a primary failure or interrupt exists. This does not add supervision for arbitrary process crashes or a timeout around an OS pipe read that never returns.
