import clsx from "clsx";
import { CSSProperties, FC, useMemo, useRef } from "react";

import "./JsonPanel.css";
import { isBase64 } from "../utils/base64";

import { usePrismHighlight } from "./prism";

interface JSONPanelProps {
  id?: string;
  data?: unknown;
  json?: string;
  simple?: boolean;
  style?: CSSProperties;
  className?: string | string[];
}

export const JSONPanel: FC<JSONPanelProps> = ({
  id,
  json,
  data,
  simple = false,
  style,
  className,
}) => {
  const sourceCode = useMemo(() => {
    return json || data
      ? JSON.stringify(resolveBase64(data), undefined, 2)
      : "";
  }, [json, data]);

  const sourceCodeRef = useRef<HTMLDivElement | null>(null);
  usePrismHighlight(sourceCodeRef, sourceCode.length);

  return (
    <div ref={sourceCodeRef}>
      <pre
        className={clsx("json-panel", simple ? "simple" : "", className)}
        style={style}
      >
        <code id={id} className={clsx("source-code", "language-javascript")}>
          {sourceCode}
        </code>
      </pre>
    </div>
  );
};

const resolveBase64 = (value: unknown): unknown => {
  const prefix = "data:image";

  // Handle arrays recursively
  if (Array.isArray(value)) {
    return value.map((v) => resolveBase64(v));
  }

  // Handle objects recursively
  if (value && typeof value === "object") {
    const resolvedObject: Record<string, unknown> = {};
    for (const key of Object.keys(value)) {
      const record = value as Record<string, unknown>;
      resolvedObject[key] = resolveBase64(record[key]);
    }
    return resolvedObject;
  }

  // Handle string values with protocol references
  if (typeof value === "string") {
    let resolvedValue = value;
    if (resolvedValue.startsWith(prefix)) {
      resolvedValue = "[base64 image]";
    } else if (isBase64(resolvedValue)) {
      resolvedValue = "[base64 data]";
    }
    return resolvedValue;
  }

  // Return unchanged for other types
  return value;
};

export default JSONPanel;
