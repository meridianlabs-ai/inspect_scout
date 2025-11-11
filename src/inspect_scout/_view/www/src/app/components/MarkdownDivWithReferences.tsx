import clsx from "clsx";
import { FC, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { MarkdownDiv } from "../../components/MarkdownDiv";
import { NoContentsPanel } from "../../components/NoContentsPanel";
import { PopOver } from "../../components/PopOver";
import { useStore } from "../../state/store";

import styles from "./MarkdownDivWithReferences.module.css";

export interface MarkdownReference {
  id: string;
  cite: string;
  renderCitePreview: () => React.ReactNode;
  url?: string;
}

interface MarkdownDivWithReferencesProps {
  markdown: string;
  references: MarkdownReference[];
  className?: string | string[];
}

export const MarkdownDivWithReferences: FC<MarkdownDivWithReferencesProps> = ({
  markdown,
  references,
  className,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [positionEl, setPositionEl] = useState<HTMLElement | null>(null);
  const [currentRef, setCurrentRef] = useState<MarkdownReference | null>(null);

  const showingRefPopover = useStore((state) => state.showingRefPopover);
  const setShowingRefPopover = useStore((state) => state.setShowingRefPopover);

  // Create a map for quick lookup of references by ID
  const refMap = useMemo(
    () => new Map(references.map((ref) => [ref.id, ref])),
    [references]
  );

  // Post-process the rendered HTML to inject reference links
  const postProcess = useCallback(
    (html: string): string => {
      let processedHtml = html;

      // Replace each reference cite with a link
      references.forEach((ref) => {
        // Escape special regex characters in the cite text
        const escapedCite = ref.cite.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const regex = new RegExp(escapedCite, "g");

        const href = ref.url || "javascript:void(0)";
        const replacement = `<a href="${href}" class="${styles.cite}" data-ref-id="${ref.id}">${ref.cite}</a>`;

        processedHtml = processedHtml.replace(regex, replacement);
      });

      return processedHtml;
    },
    [references, styles.cite]
  );

  // Memoize the MarkdownDiv to prevent re-renders when popover state changes
  // This keeps the DOM stable so event handlers remain attached
  const memoizedMarkdown = useMemo(
    () => <MarkdownDiv markdown={markdown} postProcess={postProcess} />,
    [markdown, postProcess]
  );

  // Attach event handlers to reference links after render
  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    // Find all cite links
    const citeLinks = container.querySelectorAll<HTMLElement>(
      `.${styles.cite}`
    );

    const handleMouseEnter = (e: MouseEvent): void => {
      // Identify the ref
      const el = e.currentTarget as HTMLElement;
      const id = el.getAttribute("data-ref-id");
      const ref = refMap.get(id);
      if (!ref) {
        return;
      }

      // Just set which cite we're tracking
      // PopOver will handle all show/hide logic including hover delays
      setPositionEl(el);
      setCurrentRef(ref);
      setShowingRefPopover(popoverKey(ref));
    };

    const handleClick = (e: MouseEvent): void => {
      // Stop propagation to prevent parent Link components from handling the click
      e.stopPropagation();
    };

    // Mouse handling to activate the popover
    const cleanup: Array<() => void> = [];
    citeLinks.forEach((link) => {
      link.addEventListener("mouseenter", handleMouseEnter);
      link.addEventListener("click", handleClick);

      cleanup.push(() => {
        link.removeEventListener("mouseenter", handleMouseEnter);
        link.removeEventListener("click", handleClick);
      });
    });

    // Cleanup all handlers
    return () => {
      cleanup.forEach((fn) => fn());
    };
  }, [
    markdown,
    refMap,
    styles.cite,
    setPositionEl,
    setCurrentRef,
    setShowingRefPopover,
  ]);

  const key = currentRef ? popoverKey(currentRef) : null;

  return (
    <div className={clsx(className)} ref={containerRef}>
      {memoizedMarkdown}
      {positionEl && currentRef && (
        <PopOver
          id={key}
          positionEl={positionEl}
          isOpen={showingRefPopover === key}
          setIsOpen={(isOpen) => {
            if (!isOpen) {
              setShowingRefPopover(undefined);
              setCurrentRef(null);
              setPositionEl(null);
            }
          }}
          placement="auto"
          hoverDelay={200}
          showArrow={true}
        >
          {currentRef.renderCitePreview() || (
            <NoContentsPanel text="No preview available." />
          )}
        </PopOver>
      )}
    </div>
  );
};

const popoverKey = (ref: MarkdownReference) => `markdown-ref-popover-${ref.id}`;
