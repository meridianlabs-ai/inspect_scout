import {
  VscodeFormHelper,
  VscodeLabel,
  VscodeOption,
  VscodeSingleSelect,
  VscodeTextarea,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import { FC, ReactNode, useEffect, useState } from "react";

import styles from "../ProjectPanel.module.css";

// Helper to extract input value with proper typing
function getInputValue(e: Event): string {
  return (e.target as HTMLInputElement).value;
}

function getSelectValue(e: Event): string {
  return (e.target as HTMLSelectElement).value;
}

// Helper to disable spellcheck on web component shadow DOM elements
function createSpellcheckRef(selector: "input" | "textarea") {
  return (el: HTMLElement | null) => {
    if (!el) return;
    el.setAttribute("spellcheck", "false");
    const shadowEl = el.shadowRoot?.querySelector(selector);
    if (shadowEl) {
      shadowEl.setAttribute("spellcheck", "false");
    }
  };
}

// ===== TextField Component =====
interface TextFieldProps {
  id?: string;
  label: string;
  helper?: ReactNode;
  value: string | null | undefined;
  onChange: (value: string | null) => void;
  placeholder?: string;
  disabled?: boolean;
  /** Optional validation function. Returns error message if invalid, null if valid. */
  validate?: (value: string | null) => string | null;
}

export const TextField: FC<TextFieldProps> = ({
  id,
  label,
  helper,
  value,
  onChange,
  placeholder,
  disabled,
  validate,
}) => {
  // Debounce validation errors to avoid flashing during typing
  const [debouncedError, setDebouncedError] = useState<string | null>(null);
  const errorMessage = validate && !disabled ? validate(value ?? null) : null;

  useEffect(() => {
    if (errorMessage) {
      const timer = setTimeout(() => setDebouncedError(errorMessage), 1000);
      return () => clearTimeout(timer);
    } else {
      // Clear error immediately when input becomes valid
      // TODO: lint react-hooks/set-state-in-effect - consider if fixing this violation makes sense
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDebouncedError(null);
    }
  }, [errorMessage]);

  return (
    <div className={styles.field}>
      <VscodeLabel>{label}</VscodeLabel>
      {helper && <VscodeFormHelper>{helper}</VscodeFormHelper>}
      <VscodeTextfield
        id={id}
        ref={createSpellcheckRef("input")}
        value={value ?? ""}
        disabled={disabled}
        onInput={(e) => onChange(getInputValue(e) || null)}
        placeholder={placeholder}
        spellCheck={false}
        autocomplete="off"
      />
      {debouncedError && (
        <VscodeFormHelper
          style={{ color: "var(--vscode-errorForeground)", marginTop: "4px" }}
        >
          {debouncedError}
        </VscodeFormHelper>
      )}
    </div>
  );
};

// ===== TextAreaField Component =====
interface TextAreaFieldProps {
  id?: string;
  label: string;
  helper?: ReactNode;
  value: string | null | undefined;
  onChange: (value: string | null) => void;
  placeholder?: string;
  disabled?: boolean;
  rows?: number;
}

export const TextAreaField: FC<TextAreaFieldProps> = ({
  id,
  label,
  helper,
  value,
  onChange,
  placeholder,
  disabled,
  rows = 3,
}) => {
  return (
    <div className={styles.field}>
      <VscodeLabel>{label}</VscodeLabel>
      {helper && <VscodeFormHelper>{helper}</VscodeFormHelper>}
      <VscodeTextarea
        id={id}
        ref={createSpellcheckRef("textarea")}
        value={value ?? ""}
        disabled={disabled}
        onInput={(e) => onChange(getInputValue(e) || null)}
        placeholder={placeholder}
        rows={rows}
        spellCheck={false}
        autocomplete="off"
      />
    </div>
  );
};

// ===== KeyValueField Component =====
// Handles key=value pairs (one per line) or plain string values

/**
 * Convert an object or string to key=value lines for display.
 */
export function objectToKeyValueLines(
  value: Record<string, unknown> | string | null | undefined
): string {
  if (!value) return "";
  if (typeof value === "string") return value;
  return Object.entries(value)
    .map(([k, v]) => `${k}=${String(v)}`)
    .join("\n");
}

/**
 * Parse key=value lines into an object, or return as string if it looks like a path.
 * Numeric values are preserved as numbers.
 */
export function parseKeyValueLines(
  text: string | null
): Record<string, string | number> | string | null {
  if (!text?.trim()) return null;

  // If it looks like a file path, return as string
  const trimmed = text.trim();
  if (
    trimmed.startsWith("/") ||
    trimmed.startsWith("./") ||
    trimmed.startsWith("~") ||
    /^[a-zA-Z]:\\/.test(trimmed) // Windows path
  ) {
    return trimmed;
  }

  // Parse as key=value pairs
  const result: Record<string, string | number> = {};
  for (const line of text.split("\n")) {
    const lineTrimmed = line.trim();
    if (!lineTrimmed) continue;
    const eqIndex = lineTrimmed.indexOf("=");
    if (eqIndex > 0) {
      const key = lineTrimmed.slice(0, eqIndex).trim();
      const val = lineTrimmed.slice(eqIndex + 1).trim();
      if (key) {
        // Try to parse as number if it looks numeric
        const num = Number(val);
        if (val !== "" && !isNaN(num)) {
          result[key] = num;
        } else {
          result[key] = val;
        }
      }
    }
  }

  return Object.keys(result).length > 0 ? result : null;
}

interface KeyValueFieldProps {
  id?: string;
  label: string;
  helper?: ReactNode;
  value: Record<string, unknown> | string | null | undefined;
  onChange: (value: Record<string, string | number> | string | null) => void;
  placeholder?: string;
  disabled?: boolean;
  rows?: number;
}

export const KeyValueField: FC<KeyValueFieldProps> = ({
  id,
  label,
  helper,
  value,
  onChange,
  placeholder = "key=value",
  disabled,
  rows = 3,
}) => {
  // Use local state to allow free typing without losing input
  const [text, setText] = useState(() => objectToKeyValueLines(value));

  // Sync local state when value changes externally (e.g., after save)
  useEffect(() => {
    const configText = objectToKeyValueLines(value);
    // Only sync if parsed values differ (avoids cursor jump while typing)
    const currentParsed = parseKeyValueLines(text);
    const valueParsed = parseKeyValueLines(configText);
    if (JSON.stringify(currentParsed) !== JSON.stringify(valueParsed)) {
      setText(configText);
    }
    // TODO: lint react-hooks/exhaustive-deps - review this
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const handleInput = (newText: string) => {
    setText(newText);
    // Also update config immediately so Ctrl+S works
    onChange(parseKeyValueLines(newText));
  };

  return (
    <div className={styles.field}>
      <VscodeLabel>{label}</VscodeLabel>
      {helper && <VscodeFormHelper>{helper}</VscodeFormHelper>}
      <VscodeTextarea
        id={id}
        ref={createSpellcheckRef("textarea")}
        value={text}
        disabled={disabled}
        onInput={(e) => handleInput(getInputValue(e))}
        placeholder={placeholder}
        rows={rows}
        spellCheck={false}
        autocomplete="off"
      />
    </div>
  );
};

// ===== NumberField Component =====
interface NumberFieldProps {
  id?: string;
  label: string;
  helper?: ReactNode;
  value: number | null | undefined;
  onChange: (value: number | null) => void;
  placeholder?: string;
  disabled?: boolean;
  step?: number;
}

export const NumberField: FC<NumberFieldProps> = ({
  id,
  label,
  helper,
  value,
  onChange,
  placeholder,
  disabled,
  step,
}) => {
  const handleInput = (e: Event) => {
    const val = getInputValue(e);
    const num = step ? parseFloat(val) : parseInt(val, 10);
    onChange(isNaN(num) ? null : num);
  };

  return (
    <div className={styles.field}>
      <VscodeLabel>{label}</VscodeLabel>
      {helper && <VscodeFormHelper>{helper}</VscodeFormHelper>}
      <VscodeTextfield
        id={id}
        type="number"
        step={step}
        value={value?.toString() ?? ""}
        disabled={disabled}
        onInput={handleInput}
        placeholder={placeholder}
        spellCheck={false}
        autocomplete="off"
      />
    </div>
  );
};

// ===== SelectField Component =====
interface SelectFieldProps<T extends string> {
  id?: string;
  label: string;
  helper?: ReactNode;
  value: T | null | undefined;
  options: readonly T[];
  onChange: (value: T | null) => void;
  disabled?: boolean;
  defaultLabel?: string;
}

export function SelectField<T extends string>({
  id,
  label,
  helper,
  value,
  options,
  onChange,
  disabled,
  defaultLabel = "Default",
}: SelectFieldProps<T>): ReactNode {
  return (
    <div className={styles.field}>
      <VscodeLabel>{label}</VscodeLabel>
      {helper && <VscodeFormHelper>{helper}</VscodeFormHelper>}
      <VscodeSingleSelect
        id={id}
        value={value ?? ""}
        disabled={disabled}
        onChange={(e) => {
          const val = getSelectValue(e);
          onChange(val ? (val as T) : null);
        }}
      >
        <VscodeOption value="">{defaultLabel}</VscodeOption>
        {options.map((opt) => (
          <VscodeOption key={opt} value={opt}>
            {opt}
          </VscodeOption>
        ))}
      </VscodeSingleSelect>
    </div>
  );
}

// ===== Field Component =====
interface FieldProps {
  label: string;
  helper?: ReactNode;
  children: ReactNode;
}

export function Field({ label, helper, children }: FieldProps): ReactNode {
  return (
    <div className={styles.field}>
      <VscodeLabel>{label}</VscodeLabel>
      {helper && <VscodeFormHelper>{helper}</VscodeFormHelper>}
      {children}
    </div>
  );
}
