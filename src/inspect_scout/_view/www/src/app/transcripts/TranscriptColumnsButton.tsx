import clsx from "clsx";
import { forwardRef } from "react";

import { ApplicationIcons } from "../../components/icons";
import { ToolButton } from "../../components/ToolButton";

import styles from "./TranscriptColumnsButton.module.css";

interface TranscriptColumnsButtonProps {
  isOpen: boolean;
  onClick: () => void;
}

export const TranscriptColumnsButton = forwardRef<
  HTMLButtonElement,
  TranscriptColumnsButtonProps
>(({ isOpen, onClick }, ref) => {
  return (
    <ToolButton
      title="Select transcript columns"
      icon={ApplicationIcons.threeDots}
      onClick={onClick}
      latched={isOpen}
      className={clsx("text-size-smallestest", styles.button)}
      ref={ref}
    />
  );
});

TranscriptColumnsButton.displayName = "TranscriptColumnsButton";
