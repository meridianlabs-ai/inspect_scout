import {
  VscodeButton,
  VscodeRadio,
  VscodeRadioGroup,
} from "@vscode-elements/react-elements";
import clsx from "clsx";
import { FC, useCallback, useRef, useState } from "react";

import { AutocompleteInput } from "../../../components/AutocompleteInput";
import { ApplicationIcons } from "../../../components/icons";
import { PopOver } from "../../../components/PopOver";
import { Chip } from "../../components/Chip";

import styles from "./ValidationCaseLabelsEditor.module.css";

interface ValidationCaseLabelsEditorProps {
  /** Current labels for the validation case (null means no labels set) */
  labels: { [key: string]: boolean } | null;
  /** Unique label keys from other cases for autocomplete suggestions */
  availableLabels: string[];
  /** Callback when labels change */
  onChange: (labels: { [key: string]: boolean } | null) => void;
}

/**
 * Editor component for managing labels on a validation case.
 * Displays existing labels as chips with remove buttons,
 * and provides an "Add" chip to add new labels via popover.
 */
export const ValidationCaseLabelsEditor: FC<
  ValidationCaseLabelsEditorProps
> = ({ labels, availableLabels, onChange }) => {
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);
  const [newLabelName, setNewLabelName] = useState("");
  const [newLabelValue, setNewLabelValue] = useState("true");
  const addChipRef = useRef<HTMLDivElement>(null);

  const labelEntries = labels ? Object.entries(labels) : [];

  const handleToggleLabel = useCallback(
    (labelKey: string) => {
      if (!labels) return;
      onChange({ ...labels, [labelKey]: !labels[labelKey] });
    },
    [labels, onChange]
  );

  const handleRemoveLabel = useCallback(
    (labelKey: string) => {
      if (!labels) return;
      const updated = { ...labels };
      delete updated[labelKey];
      onChange(Object.keys(updated).length === 0 ? null : updated);
    },
    [labels, onChange]
  );

  const handleAddLabel = useCallback(() => {
    const trimmed = newLabelName.trim();
    if (!trimmed) return;

    const updated = { ...(labels ?? {}), [trimmed]: newLabelValue === "true" };
    onChange(updated);

    setNewLabelName("");
    setNewLabelValue("true");
    setIsPopoverOpen(false);
  }, [newLabelName, newLabelValue, labels, onChange]);

  const handleCancel = useCallback(() => {
    setNewLabelName("");
    setNewLabelValue("true");
    setIsPopoverOpen(false);
  }, []);

  const handleOpenPopover = useCallback(() => {
    setNewLabelName("");
    setNewLabelValue("true");
    setIsPopoverOpen(true);
  }, []);

  return (
    <>
      <div className={styles.inputContainer}>
        {labelEntries.map(([key, value]) => (
          <Chip
            key={key}
            label={key}
            value={value ? "true" : "false"}
            title={`Click to toggle "${key}" to ${value ? "false" : "true"}`}
            closeTitle={`Remove label "${key}"`}
            className={clsx(styles.labelChip, "text-size-smallest")}
            onClick={() => handleToggleLabel(key)}
            onClose={() => handleRemoveLabel(key)}
          />
        ))}
        <Chip
          ref={addChipRef}
          icon={ApplicationIcons.add}
          value="Add"
          title="Add a new label"
          className={clsx(styles.labelChip, "text-size-smallest")}
          onClick={handleOpenPopover}
        />
      </div>

      <PopOver
        id="validation-labels-add"
        isOpen={isPopoverOpen}
        setIsOpen={setIsPopoverOpen}
        // eslint-disable-next-line react-hooks/refs -- positionEl accepts null; PopOver/Popper handles this in effects
        positionEl={addChipRef.current}
        placement="bottom-start"
        showArrow={true}
        hoverDelay={-1}
        closeOnMouseLeave={false}
        styles={{
          padding: "0.4rem",
          backgroundColor: "var(--bs-light)",
        }}
      >
        <div className={styles.popoverContent}>
          <div className={styles.popoverField}>
            <label
              htmlFor="validation-label-name"
              className={clsx("text-size-smallest", styles.popoverLabel)}
            >
              Label
            </label>
            <AutocompleteInput
              id="validation-label-name"
              value={newLabelName}
              onChange={setNewLabelName}
              onCommit={handleAddLabel}
              onCancel={handleCancel}
              suggestions={availableLabels}
              placeholder="Label name"
              autoFocus={true}
              allowBrowse={availableLabels.length > 0}
            />
          </div>

          <div className={styles.popoverField}>
            <label className={clsx("text-size-smallest", styles.popoverLabel)}>
              Value
            </label>
            <VscodeRadioGroup
              onChange={(e) =>
                setNewLabelValue((e.target as HTMLInputElement).value)
              }
            >
              <VscodeRadio
                name="label-value"
                label="True"
                value="true"
                checked={newLabelValue === "true"}
              />
              <VscodeRadio
                name="label-value"
                label="False"
                value="false"
                checked={newLabelValue === "false"}
              />
            </VscodeRadioGroup>
          </div>

          <div className={styles.popoverActions}>
            <VscodeButton secondary onClick={handleCancel}>
              Cancel
            </VscodeButton>
            <VscodeButton
              onClick={handleAddLabel}
              disabled={!newLabelName.trim()}
            >
              Add
            </VscodeButton>
          </div>
        </div>
      </PopOver>
    </>
  );
};
