import {
  VscodeFormHelper,
  VscodeLabel,
  VscodeOption,
  VscodeSingleSelect,
  VscodeTextarea,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import { FC, ReactNode } from "react";

import styles from "../ProjectPanel.module.css";

// Helper to extract input value with proper typing
function getInputValue(e: Event): string {
  return (e.target as HTMLInputElement).value;
}

function getSelectValue(e: Event): string {
  return (e.target as HTMLSelectElement).value;
}

// ===== TextField Component =====
interface TextFieldProps {
  label: string;
  helper?: ReactNode;
  value: string | null | undefined;
  onChange: (value: string | null) => void;
  placeholder?: string;
  disabled?: boolean;
}

export const TextField: FC<TextFieldProps> = ({
  label,
  helper,
  value,
  onChange,
  placeholder,
  disabled,
}) => (
  <div className={styles.field}>
    <VscodeLabel>{label}</VscodeLabel>
    {helper && <VscodeFormHelper>{helper}</VscodeFormHelper>}
    <VscodeTextfield
      value={value ?? ""}
      disabled={disabled}
      onInput={(e) => onChange(getInputValue(e) || null)}
      placeholder={placeholder}
      spellCheck={false}
    />
  </div>
);

// ===== TextAreaField Component =====
interface TextAreaFieldProps {
  label: string;
  helper?: ReactNode;
  value: string | null | undefined;
  onChange: (value: string | null) => void;
  placeholder?: string;
  disabled?: boolean;
  rows?: number;
}

export const TextAreaField: FC<TextAreaFieldProps> = ({
  label,
  helper,
  value,
  onChange,
  placeholder,
  disabled,
  rows = 3,
}) => (
  <div className={styles.field}>
    <VscodeLabel>{label}</VscodeLabel>
    {helper && <VscodeFormHelper>{helper}</VscodeFormHelper>}
    <VscodeTextarea
      value={value ?? ""}
      disabled={disabled}
      onInput={(e) => onChange(getInputValue(e) || null)}
      placeholder={placeholder}
      rows={rows}
      spellCheck={false}
    />
  </div>
);

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
 */
export function parseKeyValueLines(
  text: string | null
): Record<string, string> | string | null {
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
  const result: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const lineTrimmed = line.trim();
    if (!lineTrimmed) continue;
    const eqIndex = lineTrimmed.indexOf("=");
    if (eqIndex > 0) {
      const key = lineTrimmed.slice(0, eqIndex).trim();
      const val = lineTrimmed.slice(eqIndex + 1).trim();
      if (key) {
        result[key] = val;
      }
    }
  }

  return Object.keys(result).length > 0 ? result : null;
}

interface KeyValueFieldProps {
  label: string;
  helper?: ReactNode;
  value: Record<string, unknown> | string | null | undefined;
  onChange: (value: Record<string, string> | string | null) => void;
  placeholder?: string;
  disabled?: boolean;
  rows?: number;
}

export const KeyValueField: FC<KeyValueFieldProps> = ({
  label,
  helper,
  value,
  onChange,
  placeholder = "key=value",
  disabled,
  rows = 3,
}) => {
  const displayValue = objectToKeyValueLines(value);

  const handleChange = (text: string | null) => {
    onChange(parseKeyValueLines(text));
  };

  return (
    <div className={styles.field}>
      <VscodeLabel>{label}</VscodeLabel>
      {helper && <VscodeFormHelper>{helper}</VscodeFormHelper>}
      <VscodeTextarea
        value={displayValue}
        disabled={disabled}
        onInput={(e) => handleChange(getInputValue(e) || null)}
        placeholder={placeholder}
        rows={rows}
        spellCheck={false}
      />
    </div>
  );
};

// ===== NumberField Component =====
interface NumberFieldProps {
  label: string;
  helper?: ReactNode;
  value: number | null | undefined;
  onChange: (value: number | null) => void;
  placeholder?: string;
  disabled?: boolean;
  step?: number;
}

export const NumberField: FC<NumberFieldProps> = ({
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
        type="number"
        step={step}
        value={value?.toString() ?? ""}
        disabled={disabled}
        onInput={handleInput}
        placeholder={placeholder}
        spellCheck={false}
      />
    </div>
  );
};

// ===== SelectField Component =====
interface SelectFieldProps<T extends string> {
  label: string;
  helper?: ReactNode;
  value: T | null | undefined;
  options: readonly T[];
  onChange: (value: T | null) => void;
  disabled?: boolean;
  defaultLabel?: string;
}

export function SelectField<T extends string>({
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
