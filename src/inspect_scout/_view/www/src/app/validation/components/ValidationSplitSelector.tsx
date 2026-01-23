import {
  VscodeOption,
  VscodeSingleSelect,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import { FC, useState } from "react";

import { Modal } from "../../../components/Modal";

import styles from "./ValidationSplitSelector.module.css";

interface ValidationSplitSelectorProps {
  /** Current split value (null means no split) */
  value: string | null;
  /** Available splits for the dropdown */
  existingSplits: string[];
  /** Callback when split changes */
  onChange: (split: string | null) => void;
  /** Disable the selector */
  disabled?: boolean;
  /** Additional className for the select element */
  className?: string;
  /** Label for "no split" option */
  noSplitLabel?: string;
  /** Label for "new split" option */
  newSplitLabel?: string;
}

/**
 * Reusable split selector component with built-in "New Split" modal.
 * Style-agnostic: consumers control styling via className prop.
 */
export const ValidationSplitSelector: FC<ValidationSplitSelectorProps> = ({
  value,
  existingSplits,
  onChange,
  disabled = false,
  className,
  noSplitLabel = "No split",
  newSplitLabel = "New split...",
}) => {
  // Internal modal state
  const [showCustomModal, setShowCustomModal] = useState(false);
  const [customSplitValue, setCustomSplitValue] = useState("");

  // Map null to internal sentinel value for the select
  const selectValue = value ?? "__none__";

  const handleSelectChange = (e: Event) => {
    const newValue = (e.target as HTMLSelectElement).value;
    if (newValue === "__custom__") {
      setShowCustomModal(true);
      setCustomSplitValue("");
    } else if (newValue === "__none__") {
      onChange(null);
    } else {
      onChange(newValue);
    }
  };

  const handleCustomInput = (e: Event) => {
    setCustomSplitValue((e.target as HTMLInputElement).value);
  };

  const handleCustomSubmit = () => {
    if (customSplitValue.trim()) {
      onChange(customSplitValue.trim());
    }
    setShowCustomModal(false);
    setCustomSplitValue("");
  };

  const handleModalClose = () => {
    setShowCustomModal(false);
    setCustomSplitValue("");
  };

  return (
    <>
      <VscodeSingleSelect
        value={selectValue}
        onChange={handleSelectChange}
        className={className}
        disabled={disabled}
      >
        <VscodeOption value="__none__">{noSplitLabel}</VscodeOption>
        {existingSplits.map((s) => (
          <VscodeOption key={s} value={s}>
            {s}
          </VscodeOption>
        ))}
        <VscodeOption value="__custom__">{newSplitLabel}</VscodeOption>
      </VscodeSingleSelect>

      <Modal
        show={showCustomModal}
        onHide={handleModalClose}
        onSubmit={customSplitValue.trim() ? handleCustomSubmit : undefined}
        title="New Split"
        footer={
          <>
            <button className={styles.modalButton} onClick={handleModalClose}>
              Cancel
            </button>
            <button
              className={`${styles.modalButton} ${styles.modalButtonPrimary}`}
              onClick={handleCustomSubmit}
              disabled={!customSplitValue.trim()}
            >
              Create
            </button>
          </>
        }
      >
        <div className={styles.modalContent}>
          <p>Enter a name for the new split:</p>
          <VscodeTextfield
            value={customSplitValue}
            onInput={handleCustomInput}
            placeholder="Split name"
            data-autofocus
          />
        </div>
      </Modal>
    </>
  );
};
