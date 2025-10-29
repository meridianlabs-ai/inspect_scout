/**
 * Delays the execution of code for a specified number of milliseconds.
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Creates a throttled version of a function that only invokes the original function
 * at most once per every `wait` milliseconds. The throttled function will run as much
 * as it can, without ever going more than once per `wait` duration.
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  options: { leading?: boolean; trailing?: boolean } = {}
): (...args: Parameters<T>) => ReturnType<T> {
  let args: Parameters<T> | null;
  let result: ReturnType<T>;
  let timeout: ReturnType<typeof setTimeout> | null = null;
  let previous = 0;

  const later = (): void => {
    previous = options.leading === false ? 0 : Date.now();
    timeout = null;
    result = func(...(args === null ? [] : args)) as ReturnType<T>;
    if (!timeout) {
      args = null;
    }
  };

  const throttled = (...callArgs: Parameters<T>): ReturnType<T> => {
    const now = Date.now();
    if (!previous && options.leading === false) {
      previous = now;
    }
    const remaining = wait - (now - previous);

    args = callArgs as unknown as Parameters<T>;

    if (remaining <= 0 || remaining > wait) {
      if (timeout) {
        clearTimeout(timeout);
        timeout = null;
      }
      previous = now;
      result = func(...args) as ReturnType<T>;
      if (!timeout) {
        args = null;
      }
    } else if (!timeout && options.trailing !== false) {
      timeout = setTimeout(later, remaining);
    }

    return result;
  };

  return throttled;
}

/**
 * Creates a debounced version of a function that delays invoking the function
 * until after `wait` milliseconds have passed since the last time it was invoked.
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  options: { leading?: boolean; trailing?: boolean } = {}
): (...args: Parameters<T>) => ReturnType<T> {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  let args: Parameters<T>;
  let result: ReturnType<T>;
  let lastCallTime: number | null = null;

  const later = (): void => {
    const last = Date.now() - (lastCallTime || 0);

    if (last < wait && last >= 0) {
      timeout = setTimeout(later, wait - last);
    } else {
      timeout = null;
      if (!options.leading) {
        result = func(...args) as ReturnType<T>;
        if (!timeout) {
          args = null!;
        }
      }
    }
  };

  const debounced = (...callArgs: Parameters<T>): ReturnType<T> => {
    args = callArgs;
    lastCallTime = Date.now();

    const callNow = options.leading && !timeout;

    if (!timeout) {
      timeout = setTimeout(later, wait);
    }

    if (callNow) {
      result = func(...args) as ReturnType<T>;
      args = null!;
    }

    return result;
  };

  return debounced;
}
