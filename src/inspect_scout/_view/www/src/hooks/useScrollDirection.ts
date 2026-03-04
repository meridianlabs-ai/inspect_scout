import { RefObject, useCallback, useEffect, useRef, useState } from "react";

interface UseScrollDirectionOptions {
  /** Minimum px delta before recognizing a direction change. Default: 15 */
  threshold?: number;
  /** Lock duration (ms) after a state change, matching the CSS transition.
   *  Prevents the height change from the collapse/expand animation from
   *  immediately triggering the opposite direction. Default: 250 */
  transitionLockMs?: number;
}

interface UseScrollDirectionResult {
  /** True when scrolling down past threshold while scrollTop > 10px */
  hidden: boolean;
  /** Call this when a user explicitly overrides headroom (e.g. clicks a
   *  collapse toggle). Suppresses headroom updates until the next scroll
   *  direction change. */
  lockOverride: () => void;
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

  const directionAnchorRef = useRef(0);
  const lastDirectionRef = useRef<"up" | "down">("down");
  const transitionLockedRef = useRef(false);
  const userOverrideRef = useRef(false);
  const [hidden, setHidden] = useState(false);

  // Resolve the actual DOM element from the ref.  The ref's target may be
  // conditionally rendered (null on first mount, populated later). We observe
  // DOM mutations to detect when it appears, then store it in state so the
  // scroll-listener effect re-runs.
  const [scrollEl, setScrollEl] = useState<HTMLElement | null>(
    () => scrollRef.current
  );

  useEffect(() => {
    // Already have it — sync immediately.
    if (scrollRef.current) {
      setScrollEl((prev) =>
        prev === scrollRef.current ? prev : scrollRef.current
      );
      return;
    }

    // Not yet rendered. Watch the DOM for additions so we notice as soon
    // as the ref target mounts.
    const observer = new MutationObserver(() => {
      if (scrollRef.current) {
        setScrollEl(scrollRef.current);
        observer.disconnect();
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [scrollRef]);

  // Attach the scroll listener to the resolved element.
  useEffect(() => {
    if (!scrollEl) return;

    const onScroll = () => {
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
        userOverrideRef.current = false;
      }

      // Skip updates while a collapse/expand CSS transition is settling
      if (transitionLockedRef.current) return;

      if (!userOverrideRef.current) {
        const shouldHide = direction === "down" && scrollTop > 10;
        setHidden((prev) => {
          if (prev === shouldHide) return prev;
          // Lock during the CSS transition to prevent jitter
          transitionLockedRef.current = true;
          setTimeout(() => {
            transitionLockedRef.current = false;
          }, transitionLockMs);
          return shouldHide;
        });
      }
    };

    scrollEl.addEventListener("scroll", onScroll, { passive: true });
    return () => scrollEl.removeEventListener("scroll", onScroll);
  }, [scrollEl, threshold, transitionLockMs]);

  const lockOverride = useCallback(() => {
    userOverrideRef.current = true;
  }, []);

  return { hidden, lockOverride };
}
