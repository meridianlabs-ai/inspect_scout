import clsx from "clsx";
import { JSX, useState } from "react";

import styles from "./DownloadScanButton.module.css";
import { ApplicationIcons } from "./icons";

type DownloadState = "idle" | "downloading" | "success" | "error";

interface DownloadScanButtonProps {
  location: string;
  download: (location: string) => Promise<void>;
  className?: string;
}

export const DownloadScanButton = ({
  location,
  download,
  className = "",
}: DownloadScanButtonProps): JSX.Element => {
  const [state, setState] = useState<DownloadState>("idle");

  const handleClick = async (): Promise<void> => {
    setState("downloading");
    try {
      await download(location);
      setState("success");
    } catch {
      setState("error");
    }
    setTimeout(() => {
      setState("idle");
    }, 1250);
  };

  const icon =
    state === "downloading"
      ? ApplicationIcons.running
      : state === "success"
        ? `${ApplicationIcons.confirm} primary`
        : state === "error"
          ? ApplicationIcons.error
          : ApplicationIcons.download;

  return (
    <button
      type="button"
      className={clsx("download-scan-button", styles.downloadButton, className)}
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
