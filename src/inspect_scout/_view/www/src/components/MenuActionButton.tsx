import { FC, useState } from "react";

import styles from "./MenuActionButton.module.css";

export interface MenuActionItem {
  label: string;
  value: string;
  icon?: string;
  disabled?: boolean;
}

interface MenuActionButtonProps {
  items: MenuActionItem[];
  onSelect: (value: string) => void;
  disabled?: boolean;
  title?: string;
}

export const MenuActionButton: FC<MenuActionButtonProps> = ({
  items,
  onSelect,
  disabled,
  title,
}) => {
  const [showMenu, setShowMenu] = useState(false);

  const handleSelect = (value: string) => {
    setShowMenu(false);
    onSelect(value);
  };

  return (
    <div className={styles.wrapper}>
      <button
        className={styles.iconButton}
        onClick={() => setShowMenu((prev) => !prev)}
        title={title}
        disabled={disabled}
      >
        <i className="bi-three-dots" />
      </button>
      {showMenu && (
        <>
          <div className={styles.backdrop} onClick={() => setShowMenu(false)} />
          <div className={styles.menu}>
            {items.map((item) => (
              <button
                key={item.value}
                className={styles.menuItem}
                onClick={() => handleSelect(item.value)}
                disabled={item.disabled}
              >
                {item.icon && <i className={item.icon} />}
                {item.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};
