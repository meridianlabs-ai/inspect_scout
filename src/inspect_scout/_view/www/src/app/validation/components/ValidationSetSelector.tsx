import { VscodeTextfield } from "@vscode-elements/react-elements";
import { FC, useState, useRef, useEffect, useMemo } from "react";
import { createPortal } from "react-dom";

import { Modal } from "../../../components/Modal";
import { dirname } from "../../../utils/path";
import {
  getFilenameFromUri,
  hasValidationSetExtension,
  VALIDATION_SET_EXTENSIONS,
} from "../utils";

import styles from "./ValidationSetSelector.module.css";

interface ValidationSetSelectorProps {
  validationSets: string[];
  selectedUri: string | undefined;
  onSelect: (uri: string | undefined) => void;
  /** Size trigger to fit longest option (default: false) */
  autoSize?: boolean;

  /** Adds a create new option the dropown */
  allowCreate?: boolean;
  onCreate?: (name: string) => void;

  /** Project directory path for displaying full file path in create modal */
  projectDir?: string;
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
  allowCreate = false,
  onCreate,
  projectDir,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [dropdownStyle, setDropdownStyle] = useState<React.CSSProperties>({});
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Modal state for creating new set
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newSetName, setNewSetName] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

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

  // Close dropdown on window resize to prevent orphaned positioning
  useEffect(() => {
    if (!isOpen) return;

    const handleResize = () => {
      setIsOpen(false);
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
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
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  const handleSelect = (uri: string) => {
    if (uri === "__create_new__") {
      setShowCreateModal(true);
      setNewSetName("");
      setValidationError(null);
      setIsOpen(false);
    } else {
      onSelect(uri);
      setIsOpen(false);
    }
  };

  // Check if a name has an extension (any extension, valid or not)
  const hasAnyExtension = (name: string): boolean => {
    const lastDot = name.lastIndexOf(".");
    // Has extension if there's a dot that's not at the start and has chars after it
    return lastDot > 0 && lastDot < name.length - 1;
  };

  // Check if a name is starting to type an extension (has a dot)
  const isTypingExtension = (name: string): boolean => {
    const lastDot = name.lastIndexOf(".");
    return lastDot > 0; // Has a dot that's not at the start
  };

  // Check if the partial extension could be the start of a valid extension
  const isValidPartialExtension = (name: string): boolean => {
    const lastDot = name.lastIndexOf(".");
    if (lastDot <= 0) return true; // No extension being typed

    const partialExt = name.slice(lastDot).toLowerCase();
    // Check if any valid extension starts with what the user has typed
    return VALIDATION_SET_EXTENSIONS.some((ext) => ext.startsWith(partialExt));
  };

  // Get the extension validation error for real-time feedback
  const getExtensionError = (name: string): string | null => {
    const trimmed = name.trim();
    if (!trimmed) return null;

    // If user is typing an extension that can't match any valid extension
    if (isTypingExtension(trimmed) && !isValidPartialExtension(trimmed)) {
      return `Invalid extension. Valid extensions: ${VALIDATION_SET_EXTENSIONS.join(", ")}`;
    }

    return null;
  };

  // Modal handlers
  const handleNameInput = (e: Event) => {
    setNewSetName((e.target as HTMLInputElement).value);
    setValidationError(null);
  };

  const handleCreateSubmit = () => {
    const trimmedName = newSetName.trim();
    if (!trimmedName) return;

    // Check if user provided an extension that's not valid
    if (hasAnyExtension(trimmedName) && !hasValidationSetExtension(trimmedName)) {
      setValidationError(
        `Invalid extension. Valid extensions: ${VALIDATION_SET_EXTENSIONS.join(", ")}`
      );
      return;
    }

    onCreate?.(trimmedName);
    setShowCreateModal(false);
    setNewSetName("");
    setValidationError(null);
  };

  const handleModalClose = () => {
    setShowCreateModal(false);
    setNewSetName("");
    setValidationError(null);
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

    const currentIndex = selectedUri ? validationSets.indexOf(selectedUri) : -1;

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

      {/* Create new set option */}
      {allowCreate && onCreate && (
        <>
          {validationSets.length > 0 && <div className={styles.divider} />}
          <div
            role="option"
            aria-selected={false}
            className={`${styles.item} ${styles.createOption}`}
            onClick={() => handleSelect("__create_new__")}
          >
            <div className={styles.primaryText}>Create new set...</div>
          </div>
        </>
      )}
    </div>
  ) : null;

  return (
    <>
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

      {/* Create new set modal */}
      <Modal
        show={showCreateModal}
        onHide={handleModalClose}
        onSubmit={newSetName.trim() ? handleCreateSubmit : undefined}
        title="Create New Validation Set"
        footer={
          <>
            <button className={styles.modalButton} onClick={handleModalClose}>
              Cancel
            </button>
            <button
              className={`${styles.modalButton} ${styles.modalButtonPrimary}`}
              onClick={handleCreateSubmit}
              disabled={!newSetName.trim()}
            >
              Create
            </button>
          </>
        }
      >
        <div className={styles.modalContent}>
          <p>Enter a name for the new validation set:</p>
          <VscodeTextfield
            value={newSetName}
            onInput={handleNameInput}
            placeholder="validation-set-name"
            data-autofocus
          />
          {(() => {
            const trimmedName = newSetName.trim();
            const extensionError = getExtensionError(trimmedName);
            const displayError = validationError || extensionError;
            const displayDir = projectDir?.startsWith("file://")
              ? projectDir.slice(7)
              : projectDir;

            // Show hint only if no error and we have a name and projectDir
            if (trimmedName && !displayError && displayDir) {
              // If user is providing any extension, use their filename as-is
              // Otherwise append .csv
              const filename = isTypingExtension(trimmedName)
                ? trimmedName
                : `${trimmedName}.csv`;
              return (
                <span className={styles.hint}>
                  {displayDir}/{filename}
                </span>
              );
            }

            // Show error if present
            if (displayError) {
              return <span className={styles.error}>{displayError}</span>;
            }

            return null;
          })()}
        </div>
      </Modal>
    </>
  );
};
