import clsx from "clsx";
import { CSSProperties, FC, useRef } from "react";

import { usePrismHighlight } from "./prism";
import styles from "./SourceCodePanel.module.css";

interface SourceCodePanelProps {
  id?: string;
  code: string;
  language: string;
  simple?: boolean;
  style?: CSSProperties;
  className?: string | string[];
}

export const SourceCodePanel: FC<SourceCodePanelProps> = ({
  id,
  code,
  language,
  simple = false,
  style,
  className,
}) => {
  const sourceCodeRef = useRef<HTMLDivElement | null>(null);
  usePrismHighlight(sourceCodeRef, code.length);

  return (
    <div ref={sourceCodeRef}>
      <pre
        className={clsx(
          styles.sourcePanel,
          simple ? styles.simple : "",
          className
        )}
        style={style}
      >
        <code
          id={id}
          className={clsx("source-code", styles.code, `language-${language}`)}
        >
          {code}
        </code>
      </pre>
    </div>
  );
};
