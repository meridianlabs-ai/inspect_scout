import { FC, useState, useRef, useEffect, useMemo } from "react";
import { createPortal } from "react-dom";

import { dirname } from "../../../utils/path";
import { getFilenameFromUri } from "../utils";

import styles from "./ValidationSetSelector.module.css";

interface ValidationSetSelectorProps {
  validationSets: string[];
  selectedUri: string | undefined;
  onSelect: (uri: string | undefined) => void;
  /** When true, sizes trigger to fit longest option (default: false) */
  autoSize?: boolean;
}

/**
 * Select-box component for selecting validation sets.
 * Shows collapsed trigger with 2-line display (filename + path).
 * Opens dropdown on click with keyboard navigation support.
 */
export const ValidationSetSelector: FC<ValidationSetSelectorProps> = ({
  validationSets,
  selectedUri,
  onSelect,
  autoSize = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [dropdownStyle, setDropdownStyle] = useState<React.CSSProperties>({});
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Extract display name from URI (last part of path with extension)
  const getDisplayName = (uri: string): string => {
    return getFilenameFromUri(uri);
  };

  // Find the longest display name for sizing
  const longestDisplayName = useMemo(() => {
    if (validationSets.length === 0) return "";
    return validationSets.reduce((longest, uri) => {
      const name = getDisplayName(uri);
      return name.length > longest.length ? name : longest;
    }, "");
  }, [validationSets]);

  const getDisplayPath = (uri: string): string => {
    let path = dirname(uri);
    // Strip file:// prefix for cleaner display
    if (path.startsWith("file://")) {
      path = path.slice(7);
    }
    return path;
  };

  // Update dropdown position when opening
  useEffect(() => {
    if (isOpen && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setDropdownStyle({
        position: "fixed",
        top: rect.bottom + 2,
        left: rect.left,
        width: rect.width,
      });
    }
  }, [isOpen]);

  // Close on click outside (check both container and dropdown since dropdown is in portal)
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      const isOutsideContainer =
        containerRef.current && !containerRef.current.contains(target);
      const isOutsideDropdown =
        dropdownRef.current && !dropdownRef.current.contains(target);

      if (isOutsideContainer && isOutsideDropdown) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  const handleSelect = (uri: string) => {
    onSelect(uri);
    setIsOpen(false);
  };

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === "Enter" || e.key === " " || e.key === "ArrowDown") {
        e.preventDefault();
        setIsOpen(true);
      }
      return;
    }

    const currentIndex = selectedUri
      ? validationSets.indexOf(selectedUri)
      : -1;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      const nextIndex = Math.min(currentIndex + 1, validationSets.length - 1);
      onSelect(validationSets[nextIndex]);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const prevIndex = Math.max(currentIndex - 1, 0);
      onSelect(validationSets[prevIndex]);
    } else if (e.key === "Escape") {
      setIsOpen(false);
    } else if (e.key === "Enter") {
      setIsOpen(false);
    }
  };

  const dropdown = isOpen ? (
    <div
      ref={dropdownRef}
      className={styles.dropdown}
      style={dropdownStyle}
      role="listbox"
    >
      {validationSets.map((uri) => (
        <div
          key={uri}
          role="option"
          aria-selected={selectedUri === uri}
          className={`${styles.item} ${selectedUri === uri ? styles.selected : ""}`}
          onClick={() => handleSelect(uri)}
        >
          <div className={styles.primaryText}>{getDisplayName(uri)}</div>
          <div className={styles.secondaryText}>{getDisplayPath(uri)}</div>
        </div>
      ))}
    </div>
  ) : null;

  return (
    <div ref={containerRef} className={styles.container}>
      {/* Trigger button - shows selected item */}
      <button
        ref={triggerRef}
        className={styles.trigger}
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <div className={styles.triggerContent}>
          {/* Hidden sizer to set min-width based on longest option */}
          {autoSize && (
            <span className={styles.triggerSizer} aria-hidden="true">
              {longestDisplayName}
            </span>
          )}
          {selectedUri ? (
            <span className={styles.triggerPrimary}>
              {getDisplayName(selectedUri)}
            </span>
          ) : (
            <span className={styles.triggerPlaceholder}>
              Select validation set...
            </span>
          )}
        </div>
        <span className={styles.chevron} aria-hidden="true">
          ⌃
        </span>
      </button>

      {/* Dropdown rendered via portal to escape clipping */}
      {createPortal(dropdown, document.body)}
    </div>
  );
};
