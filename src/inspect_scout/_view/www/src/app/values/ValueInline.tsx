import clsx from "clsx";
import { FC, ReactNode } from "react";

import { formatPrettyDecimal } from "../../utils/format";
import {
  ScannerCore,
  isStringValue,
  isNumberValue,
  isBooleanValue,
  isNullValue,
  isArrayValue,
  isObjectValue,
} from "../types";

import styles from "./ValueInline.module.css";

interface ValueInlineProps {
  result: ScannerCore;
}

// TODO: Implement popover viewer for object and list values
// TODO: Implement support for list results
export const ValueInline: FC<ValueInlineProps> = ({ result }): ReactNode => {
  if (isStringValue(result)) {
    return `"${result.value}"`;
  } else if (isNumberValue(result)) {
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
    return <code>[Array of length ${result.value.length}]</code>;
  } else if (isObjectValue(result)) {
    return <code>[Object object]</code>;
  } else {
    return "Unknown value type";
  }
};
