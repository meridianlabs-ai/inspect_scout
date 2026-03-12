import clsx from "clsx";
import { JSX, useState } from "react";

import styles from "./DownloadScanButton.module.css";
import { ApplicationIcons } from "./icons";

type DownloadState = "idle" | "downloading" | "success" | "error";

interface DownloadScanButtonProps {
  scansDir: string;
  scanPath: string;
  download: (scansDir: string, scanPath: string) => Promise<Blob>;
  className?: string;
}

export const DownloadScanButton = ({
  scansDir,
  scanPath,
  download,
  className = "",
}: DownloadScanButtonProps): JSX.Element => {
  const [state, setState] = useState<DownloadState>("idle");

  const handleClick = async (): Promise<void> => {
    setState("downloading");
    try {
      const blob = await download(scansDir, scanPath);
      triggerBrowserDownload(blob, `${scanPath}.zip`);
      setState("success");
    } catch {
      setState("error");
    }
    // Brief visual feedback before resetting to idle
    setTimeout(() => setState("idle"), 1250);
  };

  const icon =
    state === "downloading"
      ? ApplicationIcons.refresh
      : state === "success"
        ? `${ApplicationIcons.confirm} primary`
        : state === "error"
          ? ApplicationIcons.error
          : ApplicationIcons.download;

  return (
    <button
      type="button"
      className={clsx(
        "download-scan-button",
        styles.downloadButton,
        state === "downloading" && styles.spinning,
        className
      )}
      onClick={() => {
        void handleClick();
      }}
      aria-label="Download scan results"
      disabled={state !== "idle"}
      title="Download Scan Results"
    >
      <i className={icon} aria-hidden="true" />
    </button>
  );
};

function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
