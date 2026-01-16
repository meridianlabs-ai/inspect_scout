import { FC, useCallback, useState } from "react";

import { ApplicationIcons } from "../../../../components/icons";
import { ToolButton } from "../../../../components/ToolButton";
import { useStore } from "../../../../state/store";

export const ScannerDataframeCopyCSVButton: FC = () => {
  const gridApi = useStore((state) => state.dataframeGridApi);
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    if (!gridApi) return;

    const csvData = gridApi.getDataAsCsv();
    if (csvData) {
      void navigator.clipboard.writeText(csvData).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  }, [gridApi]);

  return (
    <ToolButton
      icon={copied ? ApplicationIcons.check : ApplicationIcons.copy}
      label={copied ? "Copied" : "Copy CSV"}
      onClick={handleCopy}
      disabled={!gridApi}
      title="Copy filtered data as CSV to clipboard"
    />
  );
};
