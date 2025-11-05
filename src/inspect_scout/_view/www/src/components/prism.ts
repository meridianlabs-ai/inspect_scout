import { highlightElement } from "prismjs";
import { RefObject, useEffect } from "react";

// Syntax highlighting strings larger than this is too slow
const kPrismRenderMaxSize = 250000;

export const usePrismHighlight = (
  containerRef: RefObject<HTMLDivElement | null>,
  contentLength: number
) => {
  useEffect(() => {
    requestAnimationFrame(() => {
      if (
        contentLength > 0 &&
        containerRef.current !== null &&
        contentLength <= kPrismRenderMaxSize
      ) {
        const codeBlocks = containerRef.current.querySelectorAll("pre code");
        codeBlocks.forEach((block) => {
          if (block.className.includes("language-")) {
            block.classList.add("sourceCode");
            highlightElement(block as HTMLElement);
          }
        });
      }
    });
  }, [contentLength, containerRef]);
};
