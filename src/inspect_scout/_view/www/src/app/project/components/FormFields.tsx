import {
  VscodeFormHelper,
  VscodeLabel,
  VscodeOption,
  VscodeSingleSelect,
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
