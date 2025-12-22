import { FC, useState, useRef, useEffect, useCallback } from "react";

import styles from "./EditableText.module.css";

interface EditableTextProps {
  value?: string;
  onValueChanged: (value: string) => void;

  icon?: string;
  placeholder?: string;

  className?: string;
}

export const EditableText: FC<EditableTextProps> = ({
  value,
  onValueChanged,
  className,
  placeholder,
  icon,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [draftValue, setDraftValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when starting editing
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const commitChanges = useCallback(() => {
    if (draftValue.trim() !== "") {
      onValueChanged(draftValue);
    }
  }, [draftValue, onValueChanged]);

  const handleEditClick = () => {
    setDraftValue(value || "");
    setIsEditing(true);
  };

  const handleBlur = () => {
    setIsEditing(false);
    commitChanges();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDraftValue(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      setIsEditing(false);
      commitChanges();
    } else if (e.key === "Escape") {
      setIsEditing(false);
    }
  };

  return (
    <div className={`${styles.container} ${className || ""}`}>
      {icon && <i className={`${icon} ${styles.icon}`} />}

      {isEditing ? (
        <input
          ref={inputRef}
          type="text"
          className={styles.input}
          value={draftValue}
          onChange={handleChange}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
        />
      ) : (
        <>
          <span className={styles.text}>{value || placeholder}</span>
          <button
            className={styles.editButton}
            onClick={handleEditClick}
            aria-label="Edit"
          >
            <i className="bi bi-pencil-square" />
          </button>
        </>
      )}
    </div>
  );
};
