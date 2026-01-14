import { FC, ReactNode, useEffect, useRef } from "react";
import { createPortal } from "react-dom";

import styles from "./Modal.module.css";

interface ModalProps {
  show: boolean;
  onHide: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

export const Modal: FC<ModalProps> = ({
  show,
  onHide,
  title,
  children,
  footer,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && show) onHide();
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [show, onHide]);

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
