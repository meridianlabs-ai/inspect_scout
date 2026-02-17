import clsx from "clsx";
import { FC, Fragment, ReactNode } from "react";

import { RecordTree } from "../../components/content/RecordTree";
import {
  MarkdownDivWithReferences,
  MarkdownReference,
} from "../../components/MarkdownDivWithReferences";
import { printArray } from "../../utils/array";
import { formatPrettyDecimal } from "../../utils/format";
import { printObject } from "../../utils/object";
import {
  ScanResultSummary,
  isStringValue,
  isNumberValue,
  isBooleanValue,
  isNullValue,
  isArrayValue,
  isObjectValue,
} from "../types";

import styles from "./Value.module.css";

interface ValueProps {
  summary: ScanResultSummary;
  references: MarkdownReference[];
  style: "inline" | "block";
  maxTableSize?: number;
  interactive?: boolean;
  options?: {
    previewRefsOnHover?: boolean;
  };
}

// TODO: Implement popover viewer for object and list values
export const Value: FC<ValueProps> = ({
  summary: result,
  references,
  style,
  maxTableSize = 5,
  interactive = false,
  options,
}): ReactNode => {
  if (isStringValue(result)) {
    return (
      <MarkdownDivWithReferences
        markdown={result.value}
        references={references}
        options={options}
      />
    );
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
    return (
      <ValueList
        value={result.value}
        summary={result}
        references={references}
        style={style}
        maxListSize={maxTableSize}
        interactive={interactive}
      />
    );
  } else if (isObjectValue(result)) {
    return (
      <ValueTable
        value={result.value}
        summary={result}
        references={references}
        style={style}
        maxTableSize={maxTableSize}
        interactive={interactive}
      />
    );
  } else {
    return "Unknown value type";
  }
};

const ValueList: FC<{
  value: unknown[];
  summary: ScanResultSummary;
  maxListSize: number;
  interactive: boolean;
  references: MarkdownReference[];
  style: "inline" | "block";
}> = ({
  value,
  summary: result,
  maxListSize,
  interactive,
  references,
  style,
}) => {
  // Display only maxListSize rows
  const itemsToDisplay = value.slice(0, maxListSize);

  // Display the rows
  return (
    <div
      className={clsx(
        styles.valueTable,
        style === "inline" ? styles.inline : styles.block
      )}
    >
      {itemsToDisplay.map((item, index) => {
        const displayValue = renderValue(
          index,
          item,
          result,
          references,
          interactive
        );
        return (
          <Fragment key={`value-table-row-${index}`}>
            <div
              className={clsx(
                styles.valueKey,
                "text-style-label",
                "text-style-secondary",
                "text-size-smallest"
              )}
            >
              [{index}]
            </div>
            <div className={clsx(styles.valueValue)}>{displayValue}</div>
          </Fragment>
        );
      })}
    </div>
  );
};

const ValueTable: FC<{
  value: object;
  summary: ScanResultSummary;
  maxTableSize: number;
  interactive: boolean;
  references: MarkdownReference[];
  style: "inline" | "block";
}> = ({
  value,
  summary: result,
  maxTableSize,
  interactive,
  references,
  style,
}) => {
  // Sort keys by the value (desc, so true to false), then slice 5 keys to display
  const sortedKeys = Object.keys(value).sort((a, b) => {
    const aVal = (value as Record<string, unknown>)[a];
    const bVal = (value as Record<string, unknown>)[b];
    if (typeof aVal === "boolean" && typeof bVal === "boolean") {
      return Number(bVal) - Number(aVal);
    } else if (typeof aVal === "number" && typeof bVal === "number") {
      return bVal - aVal;
    } else {
      // Keep original order if not boolean
      return 0;
    }
  });

  // Display only 5 rows
  const keysToDisplay = sortedKeys.slice(0, maxTableSize);
  const notShown = Object.keys(value).length - maxTableSize;

  // Display the rows
  return (
    <div
      className={clsx(
        styles.valueTable,
        style === "inline" ? styles.inline : styles.block
      )}
    >
      {keysToDisplay.map((key, index) => {
        const displayValue = renderValue(
          index,
          (value as Record<string, unknown>)[key],
          result,
          references,
          interactive
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
      {notShown > 0 && (
        <Fragment key={`value-table-row-more`}>
          <div
            className={clsx(
              styles.valueKey,
              "text-style-label",
              "text-style-secondary",
              "text-size-smallest"
            )}
          >
            {notShown} more…
          </div>
          <div className={clsx(styles.valueValue)}></div>
        </Fragment>
      )}
    </div>
  );
};

// Renders a simple value (don't further render objects or lists here)
const renderValue = (
  index: number,
  val: unknown,
  summary: ScanResultSummary,
  references: MarkdownReference[],
  interactive: boolean
): ReactNode => {
  if (typeof val === "string") {
    return <MarkdownDivWithReferences markdown={val} references={references} />;
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
    return !interactive ? (
      printObject(val, 35)
    ) : (
      <RecordTree
        id={`value-record-${summary.identifier}-${index}`}
        record={val as Record<string, unknown>}
      />
    );
  } else {
    return "Unknown value type";
  }
};
