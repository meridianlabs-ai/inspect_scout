import clsx from "clsx";
import { FC, useCallback, MouseEvent } from "react";

import { useStore } from "../../../../state/store";
import { ApplicationIcons } from "../../../appearance/icons";

import styles from "./ScanHeader.module.css";
import { GridDescriptor } from "./ScanResultsList";

interface ScanResultsHeaderProps {
  gridDescriptor: GridDescriptor;
}
export const ScanResultsHeader: FC<ScanResultsHeaderProps> = ({
  gridDescriptor,
}) => {
  // Column information
  const hasExplanation = gridDescriptor.columns.includes("explanation");
  const hasLabel = gridDescriptor.columns.includes("label");
  const hasError = gridDescriptor.columns.includes("error");
  const hasValidations = gridDescriptor.columns.includes("validations");

  return (
    <div
      style={gridDescriptor.gridStyle}
      className={clsx(
        styles.header,
        "text-size-smallest",
        "text-style-label",
        "text-style-secondary",
        hasExplanation ? "" : styles.noExplanation
      )}
    >
      <ColumnHeader label="Result" />
      {hasLabel && <ColumnHeader label="Label" />}
      <ColumnHeader label="Value" className={clsx(styles.value)} />
      {hasValidations && <ColumnHeader label="Validation" />}
      {hasError && <ColumnHeader label="Error" />}
    </div>
  );
};

const ColumnHeader: FC<{
  label: string;
  className?: string | string[];
}> = ({ label, className }) => {
  const sortResults = useStore((state) => state.sortResults);
  const setSortResults = useStore((state) => state.setSortResults);
  const sort = sortResults?.find((s) => s.column === label);

  const handleSort = useCallback(
    (e: MouseEvent) => {
      e.stopPropagation();
      e.preventDefault();

      const nextSortDirection =
        sort?.direction === undefined
          ? "asc"
          : sort?.direction === "asc"
            ? "desc"
            : undefined;

      if (!nextSortDirection) {
        // remove sorting for this column
        if (e.shiftKey) {
          // multi-column sort
          const newSorts = sortResults
            ? sortResults.filter((s) => s.column !== label)
            : [];
          setSortResults(newSorts.length > 0 ? newSorts : undefined);
        } else {
          setSortResults(undefined);
        }
        return;
      } else {
        if (e.shiftKey) {
          // multi-column sort
          const newSorts = sortResults ? [...sortResults] : [];
          const existingIndex = newSorts.findIndex((s) => s.column === label);
          if (existingIndex >= 0) {
            newSorts[existingIndex] = {
              column: label,
              direction: nextSortDirection,
            };
          } else {
            newSorts.push({ column: label, direction: nextSortDirection });
          }
          setSortResults(newSorts);
        } else {
          setSortResults([{ column: label, direction: nextSortDirection }]);
        }
      }
    },
    [sort, sortResults, setSortResults]
  );

  return (
    <div className={clsx(className, styles.clickable)} onClick={handleSort}>
      {label}
      {sort && (
        <i
          className={clsx(
            sort?.direction === "asc"
              ? ApplicationIcons.arrows.up
              : ApplicationIcons.arrows.down
          )}
        />
      )}
    </div>
  );
};
