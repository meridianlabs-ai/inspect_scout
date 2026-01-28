import {
  VscodeOption,
  VscodeSingleSelect,
} from "@vscode-elements/react-elements";
import { FC } from "react";

import { useDropdownPosition } from "../../../hooks/useDropdownPosition";

import styles from "./ValidationSetSelector.module.css";

type Predicate =
  | "gt"
  | "gte"
  | "lt"
  | "lte"
  | "eq"
  | "ne"
  | "contains"
  | "startswith"
  | "endswith"
  | "icontains"
  | "iequals";

const PREDICATES: { value: Predicate; label: string }[] = [
  { value: "eq", label: "Equal (eq)" },
  { value: "ne", label: "Not equal (ne)" },
  { value: "gt", label: "Greater than (gt)" },
  { value: "gte", label: "Greater or equal (gte)" },
  { value: "lt", label: "Less than (lt)" },
  { value: "lte", label: "Less or equal (lte)" },
  { value: "contains", label: "Contains" },
  { value: "startswith", label: "Starts with" },
  { value: "endswith", label: "Ends with" },
  { value: "icontains", label: "Contains (case-insensitive)" },
  { value: "iequals", label: "Equal (case-insensitive)" },
];

interface ValidationCasePredicateSelectorProps {
  value: Predicate | null;
  onChange: (predicate: Predicate) => void;
  disabled?: boolean;
}

/**
 * Dropdown component for selecting a validation case predicate.
 */
export const ValidationCasePredicateSelector: FC<
  ValidationCasePredicateSelectorProps
> = ({ value, onChange, disabled = false }) => {
  const { ref, position } = useDropdownPosition({
    optionCount: PREDICATES.length,
  });

  const handleChange = (e: Event) => {
    const newValue = (e.target as HTMLSelectElement).value as Predicate;
    onChange(newValue);
  };

  return (
    <div ref={ref} className={styles.container}>
      <VscodeSingleSelect
        position={position}
        value={value ?? "eq"}
        onChange={handleChange}
        className={styles.select}
        disabled={disabled}
      >
        {PREDICATES.map((predicate) => (
          <VscodeOption key={predicate.value} value={predicate.value}>
            {predicate.label}
          </VscodeOption>
        ))}
      </VscodeSingleSelect>
    </div>
  );
};
