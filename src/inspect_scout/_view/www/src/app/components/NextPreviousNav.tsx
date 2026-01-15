import clsx from "clsx";
import { FC, ReactNode, useEffect } from "react";

import { ApplicationIcons } from "../../components/icons";

import styles from "./NextPreviousNav.module.css";

interface NextPreviousNavProps {
  onPrevious?: () => void;
  onNext?: () => void;
  hasPrevious: boolean;
  hasNext: boolean;
  children?: ReactNode;
  enableKeyboardNav?: boolean;
}

export const NextPreviousNav: FC<NextPreviousNavProps> = ({
  onPrevious,
  onNext,
  hasPrevious,
  hasNext,
  children,
  enableKeyboardNav = true,
}) => {
  // Global keydown handler for keyboard shortcuts
  useEffect(() => {
    if (!enableKeyboardNav) {
      return;
    }

    const handleGlobalKeyDown = (e: globalThis.KeyboardEvent) => {
      // Don't handle keyboard events if focus is on an input, textarea, or select element
      const activeElement = document.activeElement;
      const isInputFocused =
        activeElement &&
        (activeElement.tagName === "INPUT" ||
          activeElement.tagName === "TEXTAREA" ||
          activeElement.tagName === "SELECT");

      if (isInputFocused) {
        return;
      }

      // Ignore if any modifier keys are pressed
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
        return;
      }

      if (e.key === "ArrowLeft" && hasPrevious && onPrevious) {
        e.preventDefault();
        onPrevious();
      } else if (e.key === "ArrowRight" && hasNext && onNext) {
        e.preventDefault();
        onNext();
      }
    };

    // Use capture phase to catch event before it reaches other handlers
    document.addEventListener("keydown", handleGlobalKeyDown, true);

    return () => {
      document.removeEventListener("keydown", handleGlobalKeyDown, true);
    };
  }, [enableKeyboardNav, hasPrevious, hasNext, onPrevious, onNext]);

  return (
    <div className={styles.container}>
      <div
        onClick={hasPrevious ? onPrevious : undefined}
        tabIndex={hasPrevious ? 0 : undefined}
        className={clsx(styles.nav, !hasPrevious && styles.disabled)}
      >
        <i className={ApplicationIcons.previous} />
      </div>
      {children && <div className={styles.center}>{children}</div>}
      <div
        onClick={hasNext ? onNext : undefined}
        tabIndex={hasNext ? 0 : undefined}
        className={clsx(styles.nav, !hasNext && styles.disabled)}
      >
        <i className={ApplicationIcons.next} />
      </div>
    </div>
  );
};
