import { VscodeButton } from "@vscode-elements/react-elements";
import { FC, ReactNode } from "react";

import styles from "./ConfirmationDialog.module.css";
import { Modal } from "./Modal";

interface ConfirmationDialogProps {
  show: boolean;
  onHide: () => void;
  onConfirm: () => void;
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmingLabel?: string;
  isConfirming?: boolean;
  warning?: string;
}

export const ConfirmationDialog: FC<ConfirmationDialogProps> = ({
  show,
  onHide,
  onConfirm,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  confirmingLabel = "Confirming...",
  isConfirming = false,
  warning,
}) => {
  return (
    <Modal
      show={show}
      onHide={onHide}
      onSubmit={isConfirming ? undefined : onConfirm}
      title={title}
      footer={
        <>
          <VscodeButton secondary onClick={onHide}>
            {cancelLabel}
          </VscodeButton>
          <VscodeButton onClick={onConfirm} disabled={isConfirming}>
            {isConfirming ? confirmingLabel : confirmLabel}
          </VscodeButton>
        </>
      }
    >
      <div className={styles.content}>
        <p>{message}</p>
        {warning && <p className={styles.warning}>{warning}</p>}
      </div>
    </Modal>
  );
};
