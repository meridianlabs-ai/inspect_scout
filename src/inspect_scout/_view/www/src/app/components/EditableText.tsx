import clsx from "clsx";
import { FC, useRef, useCallback } from "react";

import styles from "./EditableText.module.css";

interface EditableTextProps {
  value?: string;
  mru?: string[];
  onValueChanged: (value: string) => void;

  label?: string;
  icon?: string;
  placeholder?: string;

  className?: string;
}

export const EditableText: FC<EditableTextProps> = ({
  value,
  onValueChanged,
  label,
  icon,
  placeholder,
  className,
}) => {
  const spanRef = useRef<HTMLSpanElement>(null);
  const initialValueRef = useRef<string>("");

  const handleFocus = () => {
    // Store the initial value when focusing
    if (spanRef.current) {
      initialValueRef.current = spanRef.current.textContent || "";
      // Select all text on focus
      const range = document.createRange();
      range.selectNodeContents(spanRef.current);
      const selection = window.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(range);
    }
  };

  const commitChanges = useCallback(() => {
    if (spanRef.current) {
      const newValue = spanRef.current.textContent?.trim() || "";
      if (newValue !== "" && newValue !== initialValueRef.current) {
        onValueChanged(newValue);
      } else if (newValue === "") {
        // Restore the original value if empty
        spanRef.current.textContent = initialValueRef.current;
      }
    }
  }, [onValueChanged]);

  const handleBlur = () => {
    commitChanges();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLSpanElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      spanRef.current?.blur();
    } else if (e.key === "Escape") {
      e.preventDefault();
      // Restore original value on escape
      if (spanRef.current) {
        spanRef.current.textContent = initialValueRef.current;
      }
      spanRef.current?.blur();
    }
  };

  const handleInput = () => {
    // Prevent empty content from collapsing the span
    if (spanRef.current && spanRef.current.textContent === "") {
      spanRef.current.textContent = "";
    }
  };

  const displayValue = value || placeholder || "";

  return (
    <div className={clsx(styles.container, className)}>
      <div className={clsx(styles.labelContainer)}>
        {icon && <i className={`${icon} ${styles.icon}`} />}
        {label && <span className={styles.label}>{label}</span>}
      </div>
      <span
        ref={spanRef}
        contentEditable="true"
        className={`${styles.text} ${!value ? styles.placeholder : ""}`}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        suppressContentEditableWarning
      >
        {displayValue}
      </span>
    </div>
  );
};
