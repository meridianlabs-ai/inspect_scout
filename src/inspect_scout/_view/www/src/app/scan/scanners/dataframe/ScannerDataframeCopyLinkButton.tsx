import { FC, useCallback } from "react";

import { ApplicationIcons } from "../../../../components/icons";
import { ToolButton } from "../../../../components/ToolButton";

import { useOperationStatus } from "./useOperationStatus";

export const ScannerDataframeCopyLinkButton: FC = () => {
  const [status, setStatus] = useOperationStatus();

  const handleCopy = useCallback(() => {
    if (!navigator.clipboard) {
      console.error("Clipboard API not available (requires HTTPS)");
      setStatus("error");
      return;
    }

    navigator.clipboard.writeText(window.location.href).then(
      () => setStatus("success"),
      (err: unknown) => {
        console.error("Failed to copy link to clipboard:", err);
        setStatus("error");
      }
    );
  }, [setStatus]);

  const icon =
    status === "error"
      ? ApplicationIcons.error
      : status === "success"
        ? ApplicationIcons.check
        : ApplicationIcons.link;

  const label =
    status === "error"
      ? "Failed"
      : status === "success"
        ? "Copied!"
        : "Copy Link";

  return (
    <ToolButton
      icon={icon}
      label={label}
      onClick={handleCopy}
      title="Copy link with current column selection"
      subtle={true}
    />
  );
};
