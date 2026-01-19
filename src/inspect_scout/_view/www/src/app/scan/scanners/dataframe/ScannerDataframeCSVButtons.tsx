import { FC, useCallback, useEffect, useRef, useState } from "react";

import { ApplicationIcons } from "../../../../components/icons";
import { ToolButton } from "../../../../components/ToolButton";
import { useStore } from "../../../../state/store";

import { useDataframeGridApi } from "./DataframeGridApiContext";

/**
 * Sanitize a string for use as a filename by replacing invalid characters.
 */
const sanitizeFilename = (name: string): string =>
  name.replace(/[/\\<>:"|?*]/g, "_");

/**
 * Generate a timestamp string suitable for filenames (e.g., "20240116T120000").
 */
const getFileTimestamp = (): string =>
  new Date().toISOString().slice(0, 19).replace(/[:-]/g, "");

/**
 * Button to copy filtered dataframe data as CSV to clipboard.
 */
export const ScannerDataframeCopyCSVButton: FC = () => {
  const gridApi = useDataframeGridApi();
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(false);
  const timeoutRef = useRef<number | null>(null);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const handleCopy = useCallback(() => {
    if (!gridApi) return;

    setError(false);

    let csvData: string | undefined;
    try {
      csvData = gridApi.getDataAsCsv();
    } catch (e) {
      console.error("Failed to get CSV data from grid:", e);
      setError(true);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      timeoutRef.current = window.setTimeout(() => setError(false), 2000);
      return;
    }

    if (!csvData) {
      // No data to copy (empty or all filtered out)
      return;
    }

    navigator.clipboard
      .writeText(csvData)
      .then(() => {
        setCopied(true);
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        timeoutRef.current = window.setTimeout(() => setCopied(false), 2000);
      })
      .catch((err: unknown) => {
        console.error("Failed to copy CSV to clipboard:", err);
        setError(true);
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        timeoutRef.current = window.setTimeout(() => setError(false), 2000);
      });
  }, [gridApi]);

  const icon = error
    ? ApplicationIcons.error
    : copied
      ? ApplicationIcons.check
      : ApplicationIcons.copy;

  const label = error ? "Failed" : copied ? "Copied" : "Copy CSV";

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
 */
export const ScannerDataframeDownloadCSVButton: FC = () => {
  const gridApi = useDataframeGridApi();
  const selectedScanner = useStore((state) => state.selectedScanner);

  const handleDownload = useCallback(() => {
    if (!gridApi) return;

    try {
      const timestamp = getFileTimestamp();
      const scannerName = sanitizeFilename(selectedScanner ?? "scan");
      const fileName = `${scannerName}_${timestamp}.csv`;

      gridApi.exportDataAsCsv({ fileName });
    } catch (e) {
      console.error("Failed to export CSV:", e);
    }
  }, [gridApi, selectedScanner]);

  return (
    <ToolButton
      icon={ApplicationIcons.download}
      label="Download CSV"
      onClick={handleDownload}
      title="Download filtered data as CSV file"
      subtle={true}
    />
  );
};
