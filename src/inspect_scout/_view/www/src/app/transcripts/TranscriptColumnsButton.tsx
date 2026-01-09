import clsx from "clsx";
import { forwardRef } from "react";

import { ApplicationIcons } from "../../components/icons";
import { ToolButton } from "../components/ToolButton";

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
      icon={ApplicationIcons.checkbox.checked}
      label="Choose Columns"
      onClick={onClick}
      latched={isOpen}
      className={clsx("text-size-smallest", styles.button)}
      ref={ref}
    />
  );
});

TranscriptColumnsButton.displayName = "TranscriptColumnsButton";
