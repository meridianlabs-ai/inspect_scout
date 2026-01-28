import {
  VscodeRadio,
  VscodeRadioGroup,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import { FC, useEffect, useState } from "react";

import { JsonValue } from "../../../types/api-types";
import { useDebouncedCallback } from "../../../utils/useDebouncedCallback";

type TargetMode = "true" | "false" | "other" | "unset";

/**
 * Determines the mode based on the target value.
 * - null/undefined = "unset" (user hasn't selected anything)
 * - "" (empty string) = "other" (user selected "Other" but hasn't typed a value)
 * - "true"/true = "true"
 * - "false"/false = "false"
 * - any other value = "other"
 */
function getTargetMode(target?: JsonValue): TargetMode {
  if (target === undefined || target === null) {
    return "unset";
  }
  if (target === "true" || target === true) {
    return "true";
  }
  if (target === "false" || target === false) {
    return "false";
  }
  // Empty string or any other value = "other"
  return "other";
}

interface ValidationCaseTargetEditorProps {
  target?: JsonValue;
  onChange: (newTarget: string) => void;
}

/**
 * Editor component for modifying the target of a validation case.
 */
export const ValidationCaseTargetEditor: FC<
  ValidationCaseTargetEditorProps
> = ({ target, onChange }) => {
  const [mode, setMode] = useState<TargetMode>(() => getTargetMode(target));
  const [customValue, setCustomValue] = useState(() =>
    getTargetMode(target) === "other" ? String(target ?? "") : ""
  );
  // Track when user is typing to prevent sync from overwriting during debounce
  const [isTyping, setIsTyping] = useState(false);

  // Sync mode and customValue when target prop changes externally
  // (e.g., data loads, switching cases, or after our save completes)
  // Skip sync while user is typing to avoid overwriting during debounce
  useEffect(() => {
    if (isTyping) return;

    const newMode = getTargetMode(target);
    setMode(newMode);
    if (newMode === "other") {
      setCustomValue(String(target ?? ""));
    }
  }, [target, isTyping]);

  // Debounce only the text input changes
  const debouncedOnChange = useDebouncedCallback((value: unknown) => {
    setIsTyping(false); // Clear typing flag after debounce completes
    onChange(value as string);
  }, 600);

  const handleRadioChange = (value: string) => {
    const newMode = value as TargetMode;
    setMode(newMode);

    if (newMode === "other") {
      // When switching to "other", propagate empty string as sentinel immediately
      // This distinguishes "other selected" from "never selected"
      onChange(customValue || "");
    } else {
      // Radio changes fire immediately (no debounce)
      onChange(newMode);
    }
  };

  const handleCustomValueChange = (value: string) => {
    setIsTyping(true); // Set typing flag to prevent sync during debounce
    setCustomValue(value); // Update UI immediately
    debouncedOnChange(value); // Debounce the parent callback
  };

  return (
    <div>
      <VscodeRadioGroup
        onChange={(e) =>
          handleRadioChange((e.target as HTMLInputElement).value)
        }
      >
        <VscodeRadio label="True" value="true" checked={mode === "true"} />
        <VscodeRadio label="False" value="false" checked={mode === "false"} />
        <VscodeRadio label="Other" value="other" checked={mode === "other"} />
      </VscodeRadioGroup>

      {mode === "other" && (
        <VscodeTextfield
          value={customValue}
          placeholder="Enter target value"
          onInput={(e) =>
            handleCustomValueChange((e.target as HTMLInputElement).value)
          }
          style={{ marginTop: "8px" }}
        />
      )}
    </div>
  );
};
