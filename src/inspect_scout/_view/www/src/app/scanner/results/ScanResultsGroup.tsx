import clsx from "clsx";
import { ChangeEvent, FC, useCallback } from "react";

import { useStore } from "../../../state/store";

import styles from "./ScanResultsGroup.module.css";

interface ScanResultsGroupProps {
  options: Array<"source" | "label" | "id" | "none">;
}

export const ScanResultsGroup: FC<ScanResultsGroupProps> = ({
  options = ["source", "label", "id"],
}) => {
  const setGroupResultsBy = useStore((state) => state.setGroupResultsBy);
  const groupResultsBy = useStore((state) => state.groupResultsBy);

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLSelectElement>) => {
      const sel = e.target as HTMLSelectElement;
      setGroupResultsBy(sel.value as "source" | "label" | "none");
    },
    [setGroupResultsBy]
  );

  const groupByOpts = [
    { label: "Source", value: "source" },
    { label: "Label", value: "label" },
    { label: "Id", value: "id" },
  ].filter((opt) => options.includes(toVal(opt.value)));
  if (groupByOpts.length === 0) {
    return null;
  }
  groupByOpts.unshift({ label: "None", value: "none" });

  return (
    <div className={styles.flex}>
      <span
        className={clsx(
          "sort-filter-label",
          "text-size-smaller",
          "text-style-label",
          "text-style-secondary",
          styles.label
        )}
      >
        Group:
      </span>
      <select
        id={"scan-result-filter"}
        className={clsx("form-select", "form-select-sm", "text-size-smaller")}
        aria-label=".sort-filter-label"
        value={groupResultsBy || "none"}
        onChange={handleChange}
      >
        {groupByOpts.map((option) => {
          return (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          );
        })}
      </select>
    </div>
  );
};

const toVal = (v: string | null): "source" | "label" | "id" | "none" => {
  if (v === "source") {
    return "source";
  } else if (v === "label") {
    return "label";
  } else if (v === "id") {
    return "id";
  } else {
    return "none";
  }
};
