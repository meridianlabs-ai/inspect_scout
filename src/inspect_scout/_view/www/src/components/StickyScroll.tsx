import {
  CSSProperties,
  FC,
  ReactNode,
  RefObject,
  useEffect,
  useRef,
  useState,
} from "react";

interface StickyScrollProps {
  children: ReactNode;
  scrollRef: RefObject<HTMLElement | null>;
  offsetTop?: number;
  zIndex?: number;
  className?: string;
  stickyClassName?: string;
  onStickyChange?: (isSticky: boolean) => void;
  /**
   * When true, the placeholder height is locked to the content's height
   * measured just before entering sticky mode. This prevents layout jumps
   * when the content shrinks while sticky (e.g. a collapsed swimlane).
   */
  preserveHeight?: boolean;
}

export const StickyScroll: FC<StickyScrollProps> = ({
  children,
  scrollRef,
  offsetTop = 0,
  zIndex = 100,
  className = "",
  stickyClassName = "is-sticky",
  onStickyChange,
  preserveHeight = false,
}) => {
  const contentRef = useRef<HTMLDivElement>(null);
  const [isSticky, setIsSticky] = useState(false);
  // Height captured just before entering sticky mode, used with preserveHeight
  // to keep the content area from collapsing when the sticky content shrinks.
  const [preStickHeight, setPreStickHeight] = useState(0);

  // Stable ref for the callback to avoid re-running the effect on identity changes.
  const onStickyChangeRef = useRef(onStickyChange);
  useEffect(() => {
    onStickyChangeRef.current = onStickyChange;
  }, [onStickyChange]);

  // Detect sticky state by comparing the element's position to the scroll
  // container on each scroll event. When the element is "stuck," its top
  // edge aligns with the container's top edge + offsetTop (within 1px).
  // This avoids a sentinel element that would break grid/flex layouts.
  useEffect(() => {
    const content = contentRef.current;
    const scrollContainer = scrollRef.current;
    if (!content || !scrollContainer) return;

    const checkSticky = () => {
      const containerTop = scrollContainer.getBoundingClientRect().top;
      const contentTop = content.getBoundingClientRect().top;
      // The element is sticky when it's at (or within 1px of) its sticky offset
      const nowSticky = contentTop <= containerTop + offsetTop + 1;

      setIsSticky((prev) => {
        if (prev === nowSticky) return prev;

        // Capture height before entering sticky mode
        if (nowSticky && preserveHeight && content) {
          setPreStickHeight(content.getBoundingClientRect().height);
        }

        onStickyChangeRef.current?.(nowSticky);
        return nowSticky;
      });
    };

    // Check immediately in case we're already scrolled past the threshold
    checkSticky();

    scrollContainer.addEventListener("scroll", checkSticky, { passive: true });
    return () => scrollContainer.removeEventListener("scroll", checkSticky);
  }, [scrollRef, offsetTop, preserveHeight]);

  const stickyStyle: CSSProperties = {
    position: "sticky",
    top: offsetTop,
    zIndex,
    // When preserveHeight is active and we're sticky, set a minimum height
    // so the sticky area doesn't shrink when the content collapses.
    minHeight: isSticky && preserveHeight ? preStickHeight : undefined,
  };

  const contentClassName =
    isSticky && stickyClassName
      ? `${className} ${stickyClassName}`.trim()
      : className;

  return (
    <div ref={contentRef} className={contentClassName} style={stickyStyle}>
      {children}
    </div>
  );
};
