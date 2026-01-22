import { FC, ReactNode, useEffect, useRef } from "react";
import { createPortal } from "react-dom";

import styles from "./Modal.module.css";

interface ModalProps {
  show: boolean;
  onHide: () => void;
  onSubmit?: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

export const Modal: FC<ModalProps> = ({
  show,
  onHide,
  onSubmit,
  title,
  children,
  footer,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);

  // Handle escape and enter keys
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!show) return;
      if (e.key === "Escape") {
        onHide();
      } else if (e.key === "Enter" && onSubmit) {
        e.preventDefault();
        onSubmit();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [show, onHide, onSubmit]);

  // Focus first element with autofocus attribute when modal opens
  useEffect(() => {
    if (show && modalRef.current) {
      const autofocusEl = modalRef.current.querySelector<HTMLElement>(
        "[autofocus], [data-autofocus]"
      );
      if (autofocusEl) {
        // Small delay to ensure web component is ready
        setTimeout(() => autofocusEl.focus(), 0);
      }
    }
  }, [show]);

  if (!show) return null;

  return createPortal(
    <div className={styles.backdrop} onClick={onHide}>
      <div
        ref={modalRef}
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.header}>
          <h3 className={styles.title}>{title}</h3>
          <button className={styles.closeButton} onClick={onHide}>
            <i className="codicon codicon-close" />
          </button>
        </div>
        <div className={styles.body}>{children}</div>
        {footer && <div className={styles.footer}>{footer}</div>}
      </div>
    </div>,
    document.body
  );
};
