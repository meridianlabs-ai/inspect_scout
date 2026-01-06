import clsx from "clsx";
import { JSX, useState } from "react";

import styles from "./CopyButton.module.css";
import { ApplicationIcons } from "./icons";

interface CopyButtonProps {
  icon?: string;
  title?: string;
  value: string;
  onCopySuccess?: () => void;
  onCopyError?: (error: Error) => void;
  className?: string;
  ariaLabel?: string;
}

export const CopyButton = ({
  icon = ApplicationIcons.copy,
  title,
  value,
  onCopySuccess,
  onCopyError,
  className = "",
  ariaLabel = "Copy to clipboard",
}: CopyButtonProps): JSX.Element => {
  const [isCopied, setIsCopied] = useState(false);

  const handleClick = async (): Promise<void> => {
    try {
      await navigator.clipboard.writeText(value);
      setIsCopied(true);
      onCopySuccess?.();

      // Reset copy state after delay
      setTimeout(() => {
        setIsCopied(false);
      }, 1250);
    } catch (error) {
      onCopyError?.(
        error instanceof Error ? error : new Error("Failed to copy")
      );
    }
  };

  return (
    <button
      type="button"
      className={clsx("copy-button", styles.copyButton, className)}
      onClick={() => {
        void handleClick();
      }}
      aria-label={ariaLabel}
      disabled={isCopied}
      title={title}
    >
      <i
        className={isCopied ? `${ApplicationIcons.confirm} primary` : icon}
        aria-hidden="true"
      />
    </button>
  );
};
