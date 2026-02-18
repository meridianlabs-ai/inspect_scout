import { r as reactExports, j as jsxRuntimeExports, g as clsx, k as reactDomExports, e as ApplicationIcons } from "./index.js";
const container = "_container_1qaxn_1";
const input = "_input_1qaxn_6";
const inputWithToggle = "_inputWithToggle_1qaxn_21";
const toggleButton = "_toggleButton_1qaxn_25";
const suggestionsList = "_suggestionsList_1qaxn_50";
const suggestionItem = "_suggestionItem_1qaxn_63";
const highlighted = "_highlighted_1qaxn_73";
const styles$1 = {
  container,
  input,
  inputWithToggle,
  toggleButton,
  suggestionsList,
  suggestionItem,
  highlighted
};
const AutocompleteInput = ({
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
  allowBrowse = false
}) => {
  const inputRef = reactExports.useRef(null);
  const [isOpen, setIsOpen] = reactExports.useState(false);
  const [highlightedIndex, setHighlightedIndex] = reactExports.useState(-1);
  const [isBrowseMode, setIsBrowseMode] = reactExports.useState(false);
  const [dropdownPosition, setDropdownPosition] = reactExports.useState(null);
  const listRef = reactExports.useRef(null);
  const containerRef = reactExports.useRef(null);
  const hasTypedRef = reactExports.useRef(false);
  const filteredSuggestions = reactExports.useMemo(() => {
    if (isBrowseMode) {
      return suggestions.filter((s) => s !== null);
    }
    if (value.length < charactersBeforeSuggesting) {
      return [];
    }
    const lowerValue = value.toLowerCase();
    return suggestions.filter((s) => {
      if (s === null) return false;
      const strValue = String(s).toLowerCase();
      if (strValue === lowerValue) return false;
      return strValue.includes(lowerValue);
    }).slice(0, maxSuggestions);
  }, [
    suggestions,
    value,
    maxSuggestions,
    charactersBeforeSuggesting,
    isBrowseMode
  ]);
  const showDropdown = isOpen && filteredSuggestions.length > 0;
  reactExports.useEffect(() => {
    if (showDropdown && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + 2,
        left: rect.left,
        width: rect.width
      });
    }
  }, [showDropdown]);
  reactExports.useEffect(() => {
    setHighlightedIndex(-1);
  }, [filteredSuggestions]);
  reactExports.useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.select();
      inputRef.current.scrollLeft = 0;
    }
  }, [autoFocus]);
  const handleFocus = reactExports.useCallback(() => {
    if (hasTypedRef.current && filteredSuggestions.length > 0) {
      setIsOpen(true);
    }
  }, [filteredSuggestions.length]);
  reactExports.useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);
  const handleInputChange = reactExports.useCallback(
    (e) => {
      hasTypedRef.current = true;
      setIsBrowseMode(false);
      onChange(e.target.value);
      setIsOpen(true);
    },
    [onChange]
  );
  const handleToggleBrowse = reactExports.useCallback(() => {
    if (isOpen && isBrowseMode) {
      setIsOpen(false);
      setIsBrowseMode(false);
    } else {
      setIsBrowseMode(true);
      setIsOpen(true);
    }
    inputRef.current?.focus();
  }, [isOpen, isBrowseMode]);
  const selectSuggestion = reactExports.useCallback(
    (suggestion) => {
      onChange(String(suggestion ?? ""));
      setIsOpen(false);
      setIsBrowseMode(false);
      inputRef.current?.focus();
    },
    [onChange, inputRef]
  );
  const handleKeyDown = reactExports.useCallback(
    (e) => {
      if (!showDropdown) {
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
          setHighlightedIndex(
            (prev) => Math.min(prev + 1, filteredSuggestions.length - 1)
          );
          break;
        case "ArrowUp":
          e.preventDefault();
          e.stopPropagation();
          setHighlightedIndex((prev) => Math.max(prev - 1, -1));
          break;
        case "Tab":
          if (highlightedIndex >= 0 && filteredSuggestions[highlightedIndex] !== void 0) {
            e.preventDefault();
            selectSuggestion(filteredSuggestions[highlightedIndex]);
          }
          break;
        case "Enter":
          e.preventDefault();
          e.stopPropagation();
          if (highlightedIndex >= 0 && filteredSuggestions[highlightedIndex] !== void 0) {
            selectSuggestion(filteredSuggestions[highlightedIndex]);
          }
          onCommit?.();
          break;
        case "Escape":
          e.preventDefault();
          e.stopPropagation();
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
      onCancel
    ]
  );
  reactExports.useEffect(() => {
    if (listRef.current && showDropdown && highlightedIndex >= 0) {
      const highlighted2 = listRef.current.children[highlightedIndex];
      highlighted2?.scrollIntoView({ block: "nearest" });
    }
  }, [highlightedIndex, showDropdown]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { ref: containerRef, className: styles$1.container, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "input",
      {
        id,
        ref: inputRef,
        type: "text",
        className: clsx(
          styles$1.input,
          allowBrowse && styles$1.inputWithToggle,
          className
        ),
        value,
        onChange: handleInputChange,
        onFocus: handleFocus,
        onKeyDown: handleKeyDown,
        disabled,
        placeholder,
        spellCheck: "false",
        autoComplete: "off",
        role: "combobox",
        "aria-expanded": showDropdown,
        "aria-autocomplete": "list",
        "aria-controls": `${id}-listbox`,
        "aria-activedescendant": showDropdown && highlightedIndex >= 0 ? `${id}-option-${highlightedIndex}` : void 0,
        autoFocus
      }
    ),
    allowBrowse && suggestions.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        type: "button",
        className: styles$1.toggleButton,
        onClick: handleToggleBrowse,
        disabled,
        tabIndex: -1,
        "aria-label": "Show all options",
        children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          "i",
          {
            className: clsx(
              "bi",
              isOpen && isBrowseMode ? "bi-chevron-up" : "bi-chevron-down"
            )
          }
        )
      }
    ),
    showDropdown && dropdownPosition && reactDomExports.createPortal(
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "ul",
        {
          id: `${id}-listbox`,
          ref: listRef,
          className: styles$1.suggestionsList,
          role: "listbox",
          style: {
            position: "fixed",
            top: dropdownPosition.top,
            left: dropdownPosition.left,
            minWidth: dropdownPosition.width,
            maxWidth: maxSuggestionWidth
          },
          children: filteredSuggestions.map((suggestion, index) => /* @__PURE__ */ jsxRuntimeExports.jsx(
            "li",
            {
              id: `${id}-option-${index}`,
              className: clsx(
                styles$1.suggestionItem,
                index === highlightedIndex && styles$1.highlighted
              ),
              role: "option",
              "aria-selected": index === highlightedIndex,
              onMouseDown: (e) => {
                e.preventDefault();
                e.stopPropagation();
                selectSuggestion(suggestion);
              },
              onMouseEnter: () => setHighlightedIndex(index),
              children: String(suggestion ?? "(null)")
            },
            String(suggestion)
          ))
        }
      ),
      document.body
    )
  ] });
};
const chip = "_chip_4n1t8_1";
const label = "_label_4n1t8_12";
const icon = "_icon_4n1t8_17";
const closeIcon = "_closeIcon_4n1t8_22";
const clickable = "_clickable_4n1t8_27";
const styles = {
  chip,
  label,
  icon,
  closeIcon,
  clickable
};
const Chip = reactExports.forwardRef(
  ({ icon: icon2, label: label2, value, title, closeTitle, onClick, onClose, className }, ref) => {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        ref,
        className: clsx(styles.chip, className),
        onClick,
        title,
        children: [
          icon2 ? /* @__PURE__ */ jsxRuntimeExports.jsx(
            "i",
            {
              className: clsx(
                icon2,
                styles.icon,
                onClick ? styles.clickable : void 0
              )
            }
          ) : void 0,
          label2 ? /* @__PURE__ */ jsxRuntimeExports.jsx(
            "span",
            {
              className: clsx(
                styles.label,
                onClick ? styles.clickable : void 0
              ),
              children: label2
            }
          ) : void 0,
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "span",
            {
              className: clsx(styles.value, onClick ? styles.clickable : void 0),
              children: value
            }
          ),
          onClose ? /* @__PURE__ */ jsxRuntimeExports.jsx(
            "i",
            {
              className: clsx(
                ApplicationIcons.xLarge,
                styles.closeIcon,
                styles.clickable
              ),
              title: closeTitle,
              onClick: (event) => {
                event.stopPropagation();
                onClose(event);
              }
            }
          ) : void 0
        ]
      }
    );
  }
);
Chip.displayName = "Chip";
export {
  AutocompleteInput as A,
  Chip as C
};
//# sourceMappingURL=Chip.js.map
