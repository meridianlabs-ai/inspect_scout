import clsx from "clsx";
import { FC, Fragment, ReactNode, useMemo } from "react";
import { useParams } from "react-router-dom";

import { MarkdownDivWithReferences } from "../../components/MarkdownDivWithReferences";
import {
  getRelativePathFromParams,
  parseScanResultPath,
  scanResultRoute,
} from "../../router/url";
import { printArray } from "../../utils/array";
import { formatPrettyDecimal } from "../../utils/format";
import { printObject } from "../../utils/object";
import {
  ScannerCore,
  isStringValue,
  isNumberValue,
  isBooleanValue,
  isNullValue,
  isArrayValue,
  isObjectValue,
} from "../types";
import { toMarkdownRefs } from "../utils/refs";

import styles from "./Value.module.css";

interface ValueProps {
  result: ScannerCore;
  style: "inline" | "block";
}

// TODO: Implement popover viewer for object and list values
// TODO: Implement support for list results
export const Value: FC<ValueProps> = ({ result, style }): ReactNode => {
  const params = useParams<{ "*": string }>();

  // Build URL to the scan result with the appropriate query parameters
  const buildUrl = useMemo(() => {
    if (!result?.uuid) {
      return (queryParams: string) => `?${queryParams}`;
    }

    // Get the scan path from the current URL params
    const relativePath = getRelativePathFromParams(params);
    const { scanPath } = parseScanResultPath(relativePath);

    return (queryParams: string) => {
      const searchParams = new URLSearchParams(queryParams);
      return `#${scanResultRoute(scanPath, result.uuid, searchParams)}`;
    };
  }, [result?.uuid, params]);

  if (isStringValue(result)) {
    return `"${result.value}"`;
  } else if (isNumberValue(result) && result.value !== null) {
    return formatPrettyDecimal(result.value);
  } else if (isBooleanValue(result)) {
    return (
      <div
        className={clsx(
          styles.boolean,
          result.value ? styles.true : styles.false
        )}
      >
        {String(result.value)}
      </div>
    );
  } else if (isNullValue(result)) {
    return <code>null</code>;
  } else if (isArrayValue(result)) {
    return <code>[Array(${result.value.length})]</code>;
  } else if (isObjectValue(result)) {
    return (
      <ValueTable
        value={result.value}
        result={result}
        buildUrl={buildUrl}
        style={style}
      />
    );
  } else {
    return "Unknown value type";
  }
};

const ValueTable: FC<{
  value: object;
  result: ScannerCore;
  buildUrl: (query: string) => string | undefined;
  style: "inline" | "block";
}> = ({ value, result, buildUrl, style }) => {
  // Display only 5 rows
  const maxRows = 5;
  const keys = Object.keys(value);
  const keysToDisplay = keys.slice(0, maxRows);

  // Display the rows
  return (
    <div
      className={clsx(
        styles.valueTable,
        style === "inline" ? styles.inline : styles.block
      )}
    >
      {keysToDisplay.map((key) => {
        const displayValue = renderValue(
          (value as Record<string, unknown>)[key],
          result,
          buildUrl
        );
        return (
          <Fragment key={`value-table-row-${key}`}>
            <div
              className={clsx(
                styles.valueKey,
                "text-style-label",
                "text-style-secondary",
                "text-size-smallest"
              )}
            >
              {key}
            </div>
            <div className={clsx(styles.valueValue)}>{displayValue}</div>
          </Fragment>
        );
      })}
    </div>
  );
};

// Renders a simple value (don't further render objects or lists here)
const renderValue = (
  val: unknown,
  result: ScannerCore,
  buildUrl: (query: string) => string | undefined
): ReactNode => {
  if (typeof val === "string") {
    const refs = toMarkdownRefs(
      result,
      (refId: string, type: "message" | "event") => {
        if (type === "message") {
          return buildUrl(`tab=Input&message=${encodeURIComponent(refId)}`);
        } else {
          return buildUrl(`tab=Input&event=${encodeURIComponent(refId)}`);
        }
      }
    );
    return <MarkdownDivWithReferences markdown={val} references={refs} />;
  } else if (typeof val === "number") {
    return formatPrettyDecimal(val);
  } else if (typeof val === "boolean") {
    return (
      <div className={clsx(styles.boolean, val ? styles.true : styles.false)}>
        {String(val)}
      </div>
    );
  } else if (val === null) {
    return <pre className={clsx(styles.value)}>null</pre>;
  } else if (Array.isArray(val)) {
    return printArray(val, 25);
  } else if (typeof val === "object") {
    return printObject(val, 35);
  } else {
    return "Unknown value type";
  }
};
