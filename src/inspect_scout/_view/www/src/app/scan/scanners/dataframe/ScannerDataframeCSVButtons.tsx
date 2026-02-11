import { FC, useCallback } from "react";

import { ApplicationIcons } from "../../../../components/icons";
import { ToolButton } from "../../../../components/ToolButton";
import { useStore } from "../../../../state/store";
import { defaultColumns } from "../types";

import { useDataframeGridApi } from "./DataframeGridApiContext";
import { useOperationStatus } from "./useOperationStatus";

/**
 * Sanitize a string for use as a filename by replacing invalid characters.
 * Returns fallback if result would be empty.
 */
const sanitizeFilename = (name: string, fallback = "scan"): string => {
  const sanitized = name.replace(/[/\\<>:"|?*]/g, "_");
  return sanitized || fallback;
};

/**
 * Generate a timestamp string suitable for filenames (e.g., "20240116T120000").
 */
const getFileTimestamp = (): string =>
  new Date().toISOString().slice(0, 19).replace(/[:-]/g, "");

/**
 * Button to copy filtered dataframe data as CSV to clipboard.
 * Exports only the currently visible columns from the column selector.
 */
export const ScannerDataframeCopyCSVButton: FC = () => {
  const gridApi = useDataframeGridApi();
  const visibleColumns = useStore((state) => state.dataframeFilterColumns);
  const [status, setStatus] = useOperationStatus();

  const handleCopy = useCallback(() => {
    if (!gridApi) return;

    // Check clipboard API availability (not available in non-secure contexts)
    if (!navigator.clipboard) {
      console.error("Clipboard API not available (requires HTTPS)");
      setStatus("error");
      return;
    }

    // Use visible columns from column selector, falling back to defaults
    const columnKeys = visibleColumns ?? defaultColumns;

    let csvData: string | undefined;
    try {
      csvData = gridApi.getDataAsCsv({ columnKeys });
    } catch (e: unknown) {
      console.error("Failed to get CSV data from grid:", e);
      setStatus("error");
      return;
    }

    if (!csvData) {
      // No data to copy (empty or all filtered out)
      setStatus("empty");
      return;
    }

    navigator.clipboard.writeText(csvData).then(
      () => setStatus("success"),
      (err: unknown) => {
        console.error("Failed to copy CSV to clipboard:", err);
        setStatus("error");
      }
    );
  }, [gridApi, visibleColumns, setStatus]);

  const icon =
    status === "error" || status === "empty"
      ? ApplicationIcons.error
      : status === "success"
        ? ApplicationIcons.check
        : ApplicationIcons.copy;

  const label =
    status === "error"
      ? "Failed"
      : status === "empty"
        ? "No data"
        : status === "success"
          ? "Copied"
          : "Copy CSV";

  return (
    <ToolButton
      icon={icon}
      label={label}
      onClick={handleCopy}
      title="Copy filtered data as CSV to clipboard"
      subtle={true}
    />
  );
};

/**
 * Button to download filtered dataframe data as a CSV file.
 * Exports only the currently visible columns from the column selector.
 */
export const ScannerDataframeDownloadCSVButton: FC = () => {
  const gridApi = useDataframeGridApi();
  const selectedScanner = useStore((state) => state.selectedScanner);
  const visibleColumns = useStore((state) => state.dataframeFilterColumns);
  const [status, setStatus] = useOperationStatus();

  const handleDownload = useCallback(() => {
    if (!gridApi) return;

    try {
      const timestamp = getFileTimestamp();
      const scannerName = sanitizeFilename(selectedScanner ?? "scan");
      const fileName = `${scannerName}_${timestamp}.csv`;

      // Use visible columns from column selector, falling back to defaults
      const columnKeys = visibleColumns ?? defaultColumns;

      gridApi.exportDataAsCsv({ fileName, columnKeys });
      setStatus("success");
    } catch (e: unknown) {
      console.error("Failed to export CSV:", e);
      setStatus("error");
    }
  }, [gridApi, selectedScanner, visibleColumns, setStatus]);

  const icon =
    status === "error"
      ? ApplicationIcons.error
      : status === "success"
        ? ApplicationIcons.check
        : ApplicationIcons.download;

  const label =
    status === "error"
      ? "Failed"
      : status === "success"
        ? "Downloaded"
        : "Download CSV";

  return (
    <ToolButton
      icon={icon}
      label={label}
      onClick={handleDownload}
      title="Download filtered data as CSV file"
      subtle={true}
    />
  );
};
