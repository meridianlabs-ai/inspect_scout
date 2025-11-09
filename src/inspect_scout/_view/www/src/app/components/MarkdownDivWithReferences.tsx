import clsx from "clsx";
import { FC, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { MarkdownDiv } from "../../components/MarkdownDiv";
import { PopOver } from "../../components/PopOver";
import { useStore } from "../../state/store";
import { ScannerReference } from "../types";

import styles from "./MarkdownDivWithReferences.module.css";

interface MarkdownDivWithReferencesProps {
  markdown: string;
  references: ScannerReference[];
  className?: string | string[];
}

export const MarkdownDivWithReferences: FC<MarkdownDivWithReferencesProps> = ({
  markdown,
  references,
  className,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [positionEl, setPositionEl] = useState<HTMLElement | null>(null);
  const [currentRef, setCurrentRef] = useState<ScannerReference | null>(null);

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

        const replacement = `<a href="javascript:void(0)" class="${styles.cite}" data-ref-id="${ref.id}" data-ref-type="${ref.type}">${ref.cite}</a>`;

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

    const cleanup: Array<() => void> = [];

    const handleMouseEnter = (e: MouseEvent): void => {
      const el = e.currentTarget as HTMLElement;
      const id = el.getAttribute("data-ref-id");

      const ref = refMap.get(id);
      if (!ref) {
        return;
      }

      setPositionEl(el);
      setCurrentRef(ref);
      setShowingRefPopover(true);
    };

    const handleMouseLeave = (e: MouseEvent): void => {
      setShowingRefPopover(false);
      setCurrentRef(null);
      setPositionEl(null);
    };

    citeLinks.forEach((link) => {
      link.addEventListener("mouseenter", handleMouseEnter);
      link.addEventListener("mouseleave", handleMouseLeave);

      cleanup.push(() => {
        link.removeEventListener("mouseenter", handleMouseEnter);
        link.removeEventListener("mouseleave", handleMouseLeave);
      });
    });

    // Cleanup all handlers
    return () => {
      cleanup.forEach((fn) => fn());
    };
  }, [markdown, refMap, styles.cite, setShowingRefPopover]);

  return (
    <div className={clsx(className)} ref={containerRef}>
      {memoizedMarkdown}
      {positionEl && currentRef && (
        <PopOver
          id={`markdown-ref-popover-${currentRef.id}`}
          positionEl={positionEl}
          isOpen={showingRefPopover}
          setIsOpen={setShowingRefPopover}
          placement="top"
          hoverDelay={-1}
          offset={[0, 8]}
          showArrow={true}
        >
          <div>
            <div>
              <strong>Type:</strong> {currentRef.type}
            </div>
            <div>
              <strong>ID:</strong> {currentRef.id}
            </div>
          </div>
        </PopOver>
      )}
    </div>
  );
};
