import { RefCallback, useCallback, useEffect, useState } from "react";

type DropdownPosition = "above" | "below";

interface UseDropdownPositionOptions {
  /** Number of options in the dropdown */
  optionCount: number;
  /** Height of each option in pixels (default: 22, from vscode-elements) */
  optionHeight?: number;
  /** Maximum number of visible options before scrolling (default: 10, from vscode-elements) */
  maxVisibleOptions?: number;
  /** Additional padding for the dropdown (default: 8) */
  padding?: number;
}

interface UseDropdownPositionResult {
  /** Ref callback to attach to the dropdown container element */
  ref: RefCallback<HTMLElement>;
  /** Computed position for the dropdown: 'above' or 'below' */
  position: DropdownPosition;
}

/**
 * Hook that determines optimal dropdown position based on available viewport space.
 *
 * Calculates whether a dropdown should open above or below its trigger element
 * by measuring available space and estimated dropdown height. Updates on window
 * resize and scroll events.
 *
 * @param options - Configuration for dropdown sizing
 * @returns Object containing ref callback and computed position
 *
 * @example
 * ```tsx
 * const { ref, position } = useDropdownPosition({ optionCount: 10 });
 * return (
 *   <div ref={ref}>
 *     <Dropdown position={position} />
 *   </div>
 * );
 * ```
 */
export function useDropdownPosition(
  options: UseDropdownPositionOptions
): UseDropdownPositionResult {
  const {
    optionCount,
    optionHeight = 22,
    maxVisibleOptions = 10,
    padding = 8,
  } = options;

  const [element, setElement] = useState<HTMLElement | null>(null);
  const [position, setPosition] = useState<DropdownPosition>("below");

  const ref: RefCallback<HTMLElement> = useCallback((node: HTMLElement | null) => {
    setElement(node);
  }, []);

  useEffect(() => {
    if (!element) {
      return;
    }

    const calculatePosition = (): void => {
      const rect = element.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const visibleOptions = Math.min(optionCount, maxVisibleOptions);
      const estimatedHeight = visibleOptions * optionHeight + padding;

      setPosition(spaceBelow >= estimatedHeight ? "below" : "above");
    };

    // Calculate initial position
    calculatePosition();

    // Debounce handler for resize and scroll events
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    const debouncedCalculate = (): void => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      timeoutId = setTimeout(calculatePosition, 100);
    };

    window.addEventListener("resize", debouncedCalculate);
    window.addEventListener("scroll", debouncedCalculate, true);

    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      window.removeEventListener("resize", debouncedCalculate);
      window.removeEventListener("scroll", debouncedCalculate, true);
    };
  }, [element, optionCount, optionHeight, maxVisibleOptions, padding]);

  return { ref, position };
}
