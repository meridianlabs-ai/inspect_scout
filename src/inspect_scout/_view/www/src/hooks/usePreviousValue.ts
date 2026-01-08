import { useState } from "react";

/**
 * Custom hook that tracks the previous value of a given input.
 *
 * This hook stores the previous value of the input parameter across renders,
 * making it useful for comparing current and previous states, detecting changes,
 * or implementing undo functionality.
 *
 * @template T - The type of the value being tracked
 * @param value - The current value to track
 * @returns The previous value, or undefined if this is the first render
 *
 * @example
 * ```tsx
 * const MyComponent = ({ count }: { count: number }) => {
 *   const previousCount = usePreviousValue(count);
 *
 *   return (
 *     <div>
 *       Current: {count}, Previous: {previousCount ?? 'none'}
 *     </div>
 *   );
 * };
 * ```
 */
export const usePreviousValue = <T>(value: T): T | undefined => {
  // Track the current value in state
  const [current, setCurrent] = useState<T>(value);
  // Track the previous value (undefined on first render)
  const [previous, setPrevious] = useState<T | undefined>(undefined);

  // During render, if the value has changed, update our state
  // Note: This pattern is safe because setState during render
  // is allowed when the update is conditional and deterministic
  if (value !== current) {
    setPrevious(current);
    setCurrent(value);
  }

  return previous;
};
