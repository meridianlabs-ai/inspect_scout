import clsx from "clsx";
import { FC, useRef, useCallback, useState, useEffect, useMemo } from "react";

import { PopOver } from "../../components/PopOver";

import styles from "./EditableText.module.css";

interface EditableTextProps {
  value?: string;
  secondaryValue?: string | null;
  onValueChanged: (value: string) => void;

  mru?: string[];
  mruMaxItems?: number;

  label?: string;
  title?: string;

  icon?: string;
  placeholder?: string;

  editable?: boolean;

  className?: string;
}

export const EditableText: FC<EditableTextProps> = ({
  value,
  secondaryValue,
  onValueChanged,
  mru,
  mruMaxItems = 10,
  icon,
  label,
  title,
  placeholder,
  editable = true,
  className,
}) => {
  const spanRef = useRef<HTMLSpanElement>(null);
  const initialValueRef = useRef<string>("");
  const containerRef = useRef<HTMLDivElement>(null);

  // MRU popover state: This isn't in the store because the values are transient (if the state is
  // restored, it is assumed that the popover should be closed / state discarded)
  const [showMruPopover, setShowMruPopover] = useState(false);
  const [selectedMruIndex, setSelectedMruIndex] = useState<number>(-1);
  const [currentText, setCurrentText] = useState<string>("");
  const [isEditing, setIsEditing] = useState(false);
  const [isFocused, setIsFocused] = useState(false);

  // Filter MRU list based on current text
  const filteredMru = useMemo(() => {
    if (!mru || mru.length === 0) return [];

    // If not editing yet (just focused) or current text equals the initial value,
    // show first mruMaxItems items
    // eslint-disable-next-line react-hooks/refs -- initialValueRef stores a snapshot set in handleFocus; safe to read as it doesn't need to trigger re-renders
    if (!isEditing || currentText === initialValueRef.current) {
      return mru.slice(0, mruMaxItems);
    }

    // Otherwise, filter and limit to mruMaxItems
    const filtered = mru
      .filter((item) =>
        item.toLowerCase().startsWith(currentText.toLowerCase())
      )
      .slice(0, mruMaxItems);

    // If no matches, still show all items so the popover doesn't disappear
    return filtered.length > 0 ? filtered : mru.slice(0, mruMaxItems);
  }, [mru, mruMaxItems, currentText, isEditing]);

  // Update showMruPopover based on whether we have filtered items and focus state
  useEffect(() => {
    setShowMruPopover(filteredMru.length > 0 && isFocused);
  }, [filteredMru, isFocused]);

  const handleFocus = () => {
    // Store the initial value when focusing
    if (spanRef.current) {
      initialValueRef.current = spanRef.current.textContent || "";
      setCurrentText(initialValueRef.current);
      setSelectedMruIndex(-1);
      setIsEditing(false); // Reset editing state on focus
      setIsFocused(true); // Mark as focused

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
    setShowMruPopover(false);
    setSelectedMruIndex(-1);
    setIsEditing(false);
  }, [onValueChanged]);

  const selectMruItem = useCallback(
    (item: string | undefined) => {
      if (spanRef.current && item) {
        spanRef.current.textContent = item;
        setCurrentText(item);
        setShowMruPopover(false);
        setSelectedMruIndex(-1);
        setIsEditing(false);
        spanRef.current.blur();
        if (item !== initialValueRef.current) {
          onValueChanged(item);
        }
      }
    },
    [onValueChanged]
  );

  const handleBlur = () => {
    // Delay both focus state and commit changes to allow click on MRU item to register
    setTimeout(() => {
      setIsFocused(false); // Mark as not focused
      commitChanges();
    }, 150);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLSpanElement>) => {
    // Handle MRU navigation when popover is open
    if (showMruPopover && filteredMru.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedMruIndex((prev) =>
          prev < filteredMru.length - 1 ? prev + 1 : prev
        );
        return;
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedMruIndex((prev) => (prev > 0 ? prev - 1 : -1));
        return;
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (selectedMruIndex >= 0 && selectedMruIndex < filteredMru.length) {
          selectMruItem(filteredMru[selectedMruIndex]);
        } else {
          spanRef.current?.blur();
        }
        return;
      } else if (e.key === "Escape") {
        e.preventDefault();
        setShowMruPopover(false);
        setSelectedMruIndex(-1);
        // Restore original value on escape
        if (spanRef.current) {
          spanRef.current.textContent = initialValueRef.current;
          setCurrentText(initialValueRef.current);
        }
        spanRef.current?.blur();
        return;
      }
    } else {
      // Default behavior when popover is not open
      if (e.key === "Enter") {
        e.preventDefault();
        spanRef.current?.blur();
      } else if (e.key === "Escape") {
        e.preventDefault();
        // Restore original value on escape
        if (spanRef.current) {
          spanRef.current.textContent = initialValueRef.current;
          setCurrentText(initialValueRef.current);
        }
        spanRef.current?.blur();
      }
    }
  };

  const handleInput = () => {
    // Update current text for filtering
    if (spanRef.current) {
      const text = spanRef.current.textContent || "";
      setCurrentText(text);
      setSelectedMruIndex(-1); // Reset selection when user types
      setIsEditing(true); // Mark as editing when user types
    }

    // Prevent empty content from collapsing the span
    if (spanRef.current && spanRef.current.textContent === "") {
      spanRef.current.textContent = "";
    }
  };

  const displayValue = value || placeholder || "";

  return (
    <>
      <div ref={containerRef} className={clsx(styles.container, className)}>
        <div className={clsx(styles.labelContainer)} title={title}>
          {icon && <i className={`${icon} ${styles.icon}`} />}
          {label && <span className={styles.label}>{label}</span>}
        </div>
        <span
          ref={spanRef}
          contentEditable={editable}
          className={clsx(
            styles.text,
            !value ? styles.placeholder : "",
            !editable ? styles.readOnly : ""
          )}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          suppressContentEditableWarning
        >
          {displayValue}
        </span>
        {secondaryValue && (
          <span
            className={clsx(
              styles.text,
              styles.placeholder,
              styles.secondary,
              !editable ? styles.readOnly : ""
            )}
          >
            {secondaryValue}
          </span>
        )}
      </div>

      {mru && mru.length > 0 && (
        <PopOver
          id="editable-text-mru-popover"
          isOpen={showMruPopover}
          setIsOpen={setShowMruPopover}
          // eslint-disable-next-line react-hooks/refs -- positionEl accepts null; PopOver/Popper handles this in effects and updates when ref is populated
          positionEl={spanRef.current}
          placement="bottom-start"
          hoverDelay={0}
          showArrow={false}
          offset={[0, 4]}
          className={clsx(styles.mruPopover, "text-size-smallest")}
        >
          <div className={styles.mruList}>
            {filteredMru.map((item, index) => (
              <div
                key={index}
                className={clsx(
                  styles.mruItem,
                  index === selectedMruIndex && styles.mruItemSelected
                )}
                onClick={() => selectMruItem(item)}
                onMouseEnter={() => setSelectedMruIndex(index)}
              >
                {item}
              </div>
            ))}
          </div>
        </PopOver>
      )}
    </>
  );
};
