import { forwardRef } from "react";

import { ColumnsButton, ColumnsButtonProps } from "../components/ColumnsButton";

// Re-export the shared component with transcript-specific defaults
export const TranscriptColumnsButton = forwardRef<
  HTMLButtonElement,
  ColumnsButtonProps
>((props, ref) => {
  return <ColumnsButton {...props} ref={ref} />;
});

TranscriptColumnsButton.displayName = "TranscriptColumnsButton";
