import { FC, useCallback } from "react";

import { ApplicationIcons } from "../../../../components/icons";
import { ToolButton } from "../../../../components/ToolButton";
import { useStore } from "../../../../state/store";

export const ScannerDataframeDownloadCSVButton: FC = () => {
  const gridApi = useStore((state) => state.dataframeGridApi);
  const selectedScanner = useStore((state) => state.selectedScanner);

  const handleDownload = useCallback(() => {
    if (!gridApi) return;

    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, "");
    const scannerName = selectedScanner || "scan";
    const fileName = `${scannerName}_${timestamp}.csv`;

    gridApi.exportDataAsCsv({
      fileName,
    });
  }, [gridApi, selectedScanner]);

  return (
    <ToolButton
      icon={ApplicationIcons.download}
      label="Download CSV"
      onClick={handleDownload}
      disabled={!gridApi}
      title="Download filtered data as CSV file"
    />
  );
};
