import { ChangeEvent, FC, useMemo } from "react";

import { formatTime } from "../../../utils/format";

import styles from "./ColumnFilterEditor.module.css";

export interface DurationInputProps {
  id: string;
  value: string;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
  disabled?: boolean;
  autoFocus?: boolean;
}

export const DurationInput: FC<DurationInputProps> = ({
  id,
  value,
  onChange,
  disabled,
  autoFocus,
}) => {
  const parsedSeconds = useMemo(() => {
    const num = Number(value);
    return Number.isFinite(num) && num >= 0 ? num : null;
  }, [value]);

  return (
    <div className={styles.durationInputWrapper}>
      <input
        id={id}
        className={styles.filterInput}
        type="number"
        spellCheck="false"
        value={value}
        onChange={onChange}
        placeholder="Seconds"
        disabled={disabled}
        step="any"
        min="0"
        autoFocus={autoFocus}
      />
      {parsedSeconds !== null && (
        <div className={styles.durationHelper}>{formatTime(parsedSeconds)}</div>
      )}
    </div>
  );
};
