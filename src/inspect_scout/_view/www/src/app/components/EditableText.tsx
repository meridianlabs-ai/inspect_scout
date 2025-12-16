import { FC, useState, useRef, useEffect, useMemo } from "react";

import { debounce } from "../../utils/sync";

import styles from "./EditableText.module.css";

interface EditableTextProps {
  text: string;
  onChange: (newText: string) => void;
  className?: string;
  placeholder?: string;
  icon?: string;
}

export const EditableText: FC<EditableTextProps> = ({
  text,
  onChange,
  className,
  placeholder,
  icon,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [value, setValue] = useState(text);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setValue(text);
  }, [text]);

  // Focuses input when starting editing
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleEditClick = () => {
    setIsEditing(true);
  };

  const handleBlur = () => {
    setIsEditing(false);
  };

  const debouncedOnChange = useMemo(() => debounce(onChange, 300), [onChange]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setValue(newValue);
    debouncedOnChange(newValue);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      setIsEditing(false);
    } else if (e.key === "Escape") {
      setValue(text);
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
          value={value}
          onChange={handleChange}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
        />
      ) : (
        <>
          <span className={styles.text}>{text || placeholder}</span>
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
