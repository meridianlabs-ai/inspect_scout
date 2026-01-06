import { CSSProperties, ForwardedRef, forwardRef } from "react";

import {
  MarkdownDivWithReferences,
  MarkdownReference,
} from "../../components/MarkdownDivWithReferences";
import { Preformatted } from "../../components/Preformatted";

interface RenderedTextProps {
  markdown: string;
  references?: MarkdownReference[];
  style?: CSSProperties;
  className?: string | string[];
  forceRender?: boolean;
  omitMedia?: boolean;
  options?: {
    previewRefsOnHover?: boolean;
  };
}

export const RenderedText = forwardRef<
  HTMLDivElement | HTMLPreElement,
  RenderedTextProps
>(
  (
    { markdown, references, style, className, forceRender, omitMedia, options },
    ref
  ) => {
    const displayMode = "rendered";
    if (forceRender || displayMode === "rendered") {
      return (
        <MarkdownDivWithReferences
          ref={ref as ForwardedRef<HTMLDivElement>}
          markdown={markdown}
          references={references}
          options={options}
          style={style}
          className={className}
          omitMedia={omitMedia}
        />
      );
    } else {
      return (
        <Preformatted
          ref={ref as ForwardedRef<HTMLPreElement>}
          text={markdown}
          style={style}
          className={className}
        />
      );
    }
  }
);
