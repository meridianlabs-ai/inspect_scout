import { RefObject, useCallback, useEffect, useRef, useState } from "react";

interface UseScrollDirectionOptions {
  /** Minimum px delta before recognizing a direction change. Default: 15 */
  threshold?: number;
  /** Lock duration (ms) after a state change, matching the CSS transition.
   *  Prevents the height change from the collapse/expand animation from
   *  immediately triggering the opposite direction. Default: 250 */
  transitionLockMs?: number;
  /** When current value is true, all scroll events are ignored and the
   *  direction anchor is reset when suppression ends. Useful for
   *  programmatic scrolls (e.g. outline click → scrollToEvent). */
  suppressRef?: React.RefObject<boolean>;
}

interface UseScrollDirectionResult {
  /** True when scrolling down past threshold while scrollTop > 10px */
  hidden: boolean;
  /** Call before a programmatic scroll or layout change that will shift
   *  scrollTop without the user actually scrolling. Resets the direction
   *  anchor to the current scrollTop and engages the transition lock so
   *  the resulting scroll-position shift is ignored.
   *
   *  @param debounce When true, each scroll event that arrives during the
   *    lock resets the expiry timer so the lock stays active until scrolling
   *    stops (useful for Virtuoso multi-pass settling). When false (default),
   *    the lock uses a fixed timeout matching the CSS transition duration. */
  resetAnchor: (debounce?: boolean) => void;
}

/**
 * Tracks scroll direction on a container element with hysteresis to prevent
 * jitter. Returns a `hidden` boolean suitable for driving headroom-style
 * show/hide behaviors.
 *
 * Uses an anchor-based threshold: the direction only changes after the user
 * scrolls at least `threshold` px from the last recognized change point.
 * After each state change, updates are suppressed for `transitionLockMs` to
 * let CSS animations settle without triggering feedback loops.
 *
 * The scroll container may be conditionally rendered (ref starts as null).
 * An internal MutationObserver on `document.body` detects when the element
 * appears so the scroll listener is attached promptly.
 */
export function useScrollDirection(
  scrollRef: RefObject<HTMLElement | null>,
  options?: UseScrollDirectionOptions
): UseScrollDirectionResult {
  const threshold = options?.threshold ?? 15;
  const transitionLockMs = options?.transitionLockMs ?? 250;
  const suppressRef = options?.suppressRef;

  const directionAnchorRef = useRef(0);
  const lastDirectionRef = useRef<"up" | "down">("down");
  const transitionLockedRef = useRef(false);
  // True when the lock was set by resetAnchor (programmatic scroll).
  // Programmatic locks debounce: each scroll event resets the timer so the
  // lock stays active while Virtuoso settles. Transition locks (from
  // setHidden) use a fixed timeout so direction reversals aren't delayed.
  const programmaticLockRef = useRef(false);
  const lockTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [hidden, setHidden] = useState(false);

  // Resolve the actual DOM element from the ref.  The ref's target may be
  // conditionally rendered (null on first mount, populated later). We observe
  // DOM mutations to detect when it appears, then store it in state so the
  // scroll-listener effect re-runs.
  const [scrollEl, setScrollEl] = useState<HTMLElement | null>(null);

  useEffect(() => {
    // Sync immediately if available.
    const sync = () => {
      setScrollEl((prev) =>
        prev === scrollRef.current ? prev : (scrollRef.current ?? null)
      );
    };
    sync();

    // The ref target may unmount and remount (e.g. navigating between
    // transcripts). A MutationObserver detects DOM changes so we can
    // re-sync whenever the element appears or disappears.
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [scrollRef]);

  // Reset hidden state when the scroll element changes (e.g. transcript
  // navigation unmounts/remounts the container). Uses "adjust state during
  // render" pattern to avoid setState-in-effect.
  const [prevScrollEl, setPrevScrollEl] = useState(scrollEl);
  if (prevScrollEl !== scrollEl) {
    setPrevScrollEl(scrollEl);
    if (hidden) {
      setHidden(false);
    }
  }

  // Attach the scroll listener to the resolved element.
  // Reset ref-based internal state when the element changes.
  useEffect(() => {
    directionAnchorRef.current = 0;
    lastDirectionRef.current = "up";
    transitionLockedRef.current = false;

    if (!scrollEl) return;

    // Track previous suppression state to reset anchor when suppression ends.
    let wasSuppressed = suppressRef?.current ?? false;

    const onScroll = () => {
      const isSuppressed = suppressRef?.current ?? false;

      // When suppression ends, reset the anchor to the current position
      // so the first real scroll after the programmatic one starts fresh.
      if (wasSuppressed && !isSuppressed) {
        directionAnchorRef.current = scrollEl.scrollTop;
      }
      wasSuppressed = isSuppressed;

      if (isSuppressed) {
        // Keep the anchor tracking during suppression so the threshold
        // doesn't accumulate a large delta across the programmatic scroll.
        directionAnchorRef.current = scrollEl.scrollTop;
        return;
      }

      const scrollTop = scrollEl.scrollTop;

      // At the very top — always reveal headroom and reset anchor so the
      // threshold doesn't fight subsequent downward scrolls.
      if (scrollTop <= 0) {
        directionAnchorRef.current = 0;
        lastDirectionRef.current = "up";
        if (!transitionLockedRef.current) {
          setHidden(false);
        }
        return;
      }

      const delta = scrollTop - directionAnchorRef.current;

      // Only recognize a direction change after exceeding the threshold
      // from the anchor point. This avoids jitter from sub-pixel scrolls
      // and from collapse/expand animations shifting content.
      if (Math.abs(delta) < threshold) return;

      const direction = delta > 0 ? "down" : "up";
      const directionChanged = direction !== lastDirectionRef.current;

      // Move the anchor to current position for the next threshold check
      directionAnchorRef.current = scrollTop;

      if (directionChanged) {
        lastDirectionRef.current = direction;
      }

      // Skip updates while locked.
      if (transitionLockedRef.current) {
        // Programmatic locks (from resetAnchor) debounce: each scroll event
        // resets the timer so the lock stays active while Virtuoso settles
        // across multiple adjustment passes.
        if (programmaticLockRef.current && lockTimerRef.current !== null) {
          clearTimeout(lockTimerRef.current);
          lockTimerRef.current = setTimeout(() => {
            transitionLockedRef.current = false;
            programmaticLockRef.current = false;
            lockTimerRef.current = null;
            // Reset anchor to final settled position
            directionAnchorRef.current = scrollEl.scrollTop;
          }, transitionLockMs);
        }
        // Transition locks (from setHidden) use a fixed timeout — no
        // debouncing, so direction reversals during normal scrolling
        // are detected promptly after the CSS animation settles.
        return;
      }

      const shouldHide = direction === "down" && scrollTop > 10;
      setHidden((prev) => {
        if (prev === shouldHide) return prev;
        // Lock during the CSS transition to prevent jitter
        transitionLockedRef.current = true;
        if (lockTimerRef.current !== null) {
          clearTimeout(lockTimerRef.current);
        }
        lockTimerRef.current = setTimeout(() => {
          transitionLockedRef.current = false;
          lockTimerRef.current = null;
        }, transitionLockMs);
        return shouldHide;
      });
    };

    scrollEl.addEventListener("scroll", onScroll, { passive: true });
    return () => scrollEl.removeEventListener("scroll", onScroll);
  }, [scrollEl, threshold, transitionLockMs, suppressRef]);

  const resetAnchor = useCallback(
    (debounce?: boolean) => {
      if (scrollEl) {
        directionAnchorRef.current = scrollEl.scrollTop;
      }
      transitionLockedRef.current = true;
      programmaticLockRef.current = !!debounce;
      if (lockTimerRef.current !== null) {
        clearTimeout(lockTimerRef.current);
      }
      lockTimerRef.current = setTimeout(() => {
        transitionLockedRef.current = false;
        programmaticLockRef.current = false;
        lockTimerRef.current = null;
      }, transitionLockMs);
    },
    [scrollEl, transitionLockMs]
  );

  return { hidden, resetAnchor };
}
