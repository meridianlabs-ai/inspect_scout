import { FC, ReactNode } from "react";

import { ScannerCore } from "../types";

interface ValueProps {
  result: ScannerCore;
}

// TODO: Implement popover viewer for object and list values
export const Value: FC<ValueProps> = ({ result }): ReactNode => {
  if (result.valueType === "string") {
    return `"${String(result.value)}"`;
  } else if (result.valueType === "number" || result.valueType === "boolean") {
    return String(result.value);
  } else if (result.valueType === "null") {
    return "null";
  } else if (result.valueType === "array") {
    return `[Array of length ${(result.value as unknown[]).length}]`;
  } else if (result.valueType === "object") {
    return `{Object with keys: ${Object.keys(result.value as object).join(", ")}}`;
  } else {
    return "Unknown value type";
  }
};
