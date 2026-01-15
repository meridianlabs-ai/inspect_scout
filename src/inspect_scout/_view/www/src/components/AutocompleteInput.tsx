import clsx from "clsx";
import {
  ChangeEvent,
  FC,
  KeyboardEvent,
  RefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";

import styles from "./AutocompleteInput.module.css";

export interface AutocompleteInputProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  onCommit?: () => void;
  onCancel?: () => void;
  inputRef: RefObject<HTMLInputElement | null>;
  disabled?: boolean;
  placeholder?: string;
  suggestions: Array<string | number | boolean | null>;
  className?: string;
}

const MAX_VISIBLE_SUGGESTIONS = 10;
const MIN_CHARS_FOR_SUGGESTIONS = 3;

export const AutocompleteInput: FC<AutocompleteInputProps> = ({
  id,
  value,
  onChange,
  onCommit,
  onCancel,
  inputRef,
  disabled,
  placeholder = "Filter",
  suggestions,
  className,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  // Start with no selection (-1) so Enter submits the typed value, not a suggestion
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [dropdownPosition, setDropdownPosition] = useState<{
    top: number;
    left: number;
    width: number;
  } | null>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Filter suggestions based on current input (only when 3+ chars typed)
  const filteredSuggestions = useMemo(() => {
    if (value.length < MIN_CHARS_FOR_SUGGESTIONS) {
      return [];
    }
    const lowerValue = value.toLowerCase();
    return suggestions
      .filter((s) => {
        if (s === null) return false;
        return String(s).toLowerCase().includes(lowerValue);
      })
      .slice(0, MAX_VISIBLE_SUGGESTIONS);
  }, [suggestions, value]);

  // Determine if dropdown should be shown
  const showDropdown = isOpen && filteredSuggestions.length > 0;

  // Update dropdown position when showing
  useEffect(() => {
    if (showDropdown && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      // Use viewport coordinates since we're using position: fixed
      setDropdownPosition({
        top: rect.bottom + 2,
        left: rect.left,
        width: rect.width,
      });
    }
  }, [showDropdown]);

  // Reset highlight when suggestions change (no selection by default)
  useEffect(() => {
    setHighlightedIndex(-1);
  }, [filteredSuggestions]);

  // Show dropdown when input is focused and has suggestions
  const handleFocus = useCallback(() => {
    if (filteredSuggestions.length > 0) {
      setIsOpen(true);
    }
  }, [filteredSuggestions.length]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      onChange(e.target.value);
      setIsOpen(true);
    },
    [onChange]
  );

  const selectSuggestion = useCallback(
    (suggestion: string | number | boolean | null) => {
      onChange(String(suggestion ?? ""));
      setIsOpen(false);
      inputRef.current?.focus();
    },
    [onChange, inputRef]
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (!showDropdown) {
        // Pass through to parent handlers when dropdown is not shown
        if (e.key === "Escape") {
          e.preventDefault();
          e.stopPropagation();
          onCancel?.();
        } else if (e.key === "Enter") {
          e.preventDefault();
          e.stopPropagation();
          onCommit?.();
        }
        return;
      }

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          e.stopPropagation();
          setHighlightedIndex((prev) =>
            Math.min(prev + 1, filteredSuggestions.length - 1)
          );
          break;

        case "ArrowUp":
          e.preventDefault();
          e.stopPropagation();
          setHighlightedIndex((prev) => Math.max(prev - 1, -1));
          break;

        case "Tab":
          // Tab completes the highlighted suggestion (only if one is selected)
          if (
            highlightedIndex >= 0 &&
            filteredSuggestions[highlightedIndex] !== undefined
          ) {
            e.preventDefault();
            selectSuggestion(filteredSuggestions[highlightedIndex]);
          }
          break;

        case "Enter":
          e.preventDefault();
          e.stopPropagation();
          // Only use suggestion if one is highlighted, otherwise submit typed value
          if (
            highlightedIndex >= 0 &&
            filteredSuggestions[highlightedIndex] !== undefined
          ) {
            selectSuggestion(filteredSuggestions[highlightedIndex]);
          }
          // Always commit (either selected suggestion or typed value)
          onCommit?.();
          break;

        case "Escape":
          e.preventDefault();
          e.stopPropagation();
          // First escape closes dropdown, second cancels
          setIsOpen(false);
          break;
      }
    },
    [
      showDropdown,
      filteredSuggestions,
      highlightedIndex,
      selectSuggestion,
      onCommit,
      onCancel,
    ]
  );

  // Scroll highlighted item into view
  useEffect(() => {
    if (listRef.current && showDropdown && highlightedIndex >= 0) {
      const highlighted = listRef.current.children[
        highlightedIndex
      ] as HTMLElement;
      highlighted?.scrollIntoView({ block: "nearest" });
    }
  }, [highlightedIndex, showDropdown]);

  return (
    <div ref={containerRef} className={styles.container}>
      <input
        id={id}
        ref={inputRef}
        type="text"
        className={clsx(styles.input, className)}
        value={value}
        onChange={handleInputChange}
        onFocus={handleFocus}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder}
        spellCheck="false"
        autoComplete="off"
        role="combobox"
        aria-expanded={showDropdown}
        aria-autocomplete="list"
        aria-controls={`${id}-listbox`}
        aria-activedescendant={
          showDropdown && highlightedIndex >= 0
            ? `${id}-option-${highlightedIndex}`
            : undefined
        }
      />

      {showDropdown &&
        dropdownPosition &&
        createPortal(
          <ul
            id={`${id}-listbox`}
            ref={listRef}
            className={styles.suggestionsList}
            role="listbox"
            style={{
              position: "fixed",
              top: dropdownPosition.top,
              left: dropdownPosition.left,
              width: dropdownPosition.width,
            }}
          >
            {filteredSuggestions.map((suggestion, index) => (
              <li
                key={String(suggestion)}
                id={`${id}-option-${index}`}
                className={clsx(
                  styles.suggestionItem,
                  index === highlightedIndex && styles.highlighted
                )}
                role="option"
                aria-selected={index === highlightedIndex}
                onMouseDown={(e) => {
                  // Prevent mousedown from triggering outside click handler
                  e.preventDefault();
                  selectSuggestion(suggestion);
                }}
                onMouseEnter={() => setHighlightedIndex(index)}
              >
                {String(suggestion ?? "(null)")}
              </li>
            ))}
          </ul>,
          document.body
        )}
    </div>
  );
};
