import clsx from "clsx";
import {
  ChangeEvent,
  FC,
  KeyboardEvent,
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
  disabled?: boolean;
  placeholder?: string;
  suggestions: Array<string | number | boolean | null>;
  autoFocus?: boolean;
  maxSuggestions?: number;
  charactersBeforeSuggesting?: number;
  maxSuggestionWidth?: number;
  className?: string;
  /** When true, shows a dropdown toggle icon to browse all options */
  allowBrowse?: boolean;
}

export const AutocompleteInput: FC<AutocompleteInputProps> = ({
  id,
  value,
  onChange,
  onCommit,
  onCancel,
  disabled,
  suggestions,
  placeholder = "Filter",
  maxSuggestions = 10,
  charactersBeforeSuggesting = 1,
  maxSuggestionWidth = 300,
  autoFocus,
  className,
  allowBrowse = false,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  // Start with no selection (-1) so Enter submits the typed value, not a suggestion
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  // Track whether dropdown was opened via browse icon (shows all options)
  const [isBrowseMode, setIsBrowseMode] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState<{
    top: number;
    left: number;
    width: number;
  } | null>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  // Track whether user has typed in the input (to avoid showing suggestions on initial focus)
  const hasTypedRef = useRef(false);

  // Filter suggestions based on current input (or show all in browse mode)
  const filteredSuggestions = useMemo(() => {
    // In browse mode, show all non-null suggestions (no limit)
    if (isBrowseMode) {
      return suggestions.filter((s) => s !== null);
    }
    // Normal mode: require minimum characters before showing suggestions
    if (value.length < charactersBeforeSuggesting) {
      return [];
    }
    const lowerValue = value.toLowerCase();
    return suggestions
      .filter((s) => {
        if (s === null) return false;
        const strValue = String(s).toLowerCase();
        // Exclude exact matches - no point suggesting what's already there
        if (strValue === lowerValue) return false;
        return strValue.includes(lowerValue);
      })
      .slice(0, maxSuggestions);
  }, [
    suggestions,
    value,
    maxSuggestions,
    charactersBeforeSuggesting,
    isBrowseMode,
  ]);

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
    // TODO: lint react-hooks/set-state-in-effect - consider if fixing this violation makes sense
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHighlightedIndex(-1);
  }, [filteredSuggestions]);

  // Select all text when autoFocus is enabled (show start of text, not end)
  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.select();
      inputRef.current.scrollLeft = 0;
    }
  }, [autoFocus]);

  // Show dropdown when input is focused and has suggestions (only if user has typed)
  const handleFocus = useCallback(() => {
    if (hasTypedRef.current && filteredSuggestions.length > 0) {
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
      hasTypedRef.current = true;
      setIsBrowseMode(false); // Exit browse mode when user types
      onChange(e.target.value);
      setIsOpen(true);
    },
    [onChange]
  );

  const handleToggleBrowse = useCallback(() => {
    if (isOpen && isBrowseMode) {
      // If already open in browse mode, close it
      setIsOpen(false);
      setIsBrowseMode(false);
    } else {
      // Open in browse mode
      setIsBrowseMode(true);
      setIsOpen(true);
    }
    inputRef.current?.focus();
  }, [isOpen, isBrowseMode]);

  const selectSuggestion = useCallback(
    (suggestion: string | number | boolean | null) => {
      onChange(String(suggestion ?? ""));
      setIsOpen(false);
      setIsBrowseMode(false);
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
        className={clsx(
          styles.input,
          allowBrowse && styles.inputWithToggle,
          className
        )}
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
        autoFocus={autoFocus}
      />
      {allowBrowse && suggestions.length > 0 && (
        <button
          type="button"
          className={styles.toggleButton}
          onClick={handleToggleBrowse}
          disabled={disabled}
          tabIndex={-1}
          aria-label="Show all options"
        >
          <i
            className={clsx(
              "bi",
              isOpen && isBrowseMode ? "bi-chevron-up" : "bi-chevron-down"
            )}
          />
        </button>
      )}

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
              minWidth: dropdownPosition.width,
              maxWidth: maxSuggestionWidth,
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
                  // Prevent mousedown from triggering outside click handlers (including PopOver)
                  e.preventDefault();
                  e.stopPropagation();
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
