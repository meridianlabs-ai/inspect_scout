import clsx from "clsx";
import { FC, ReactNode } from "react";

import styles from "./Navbar.module.css";

interface NavbarProps {
  left?: ReactNode;
  right?: ReactNode;
  bordered?: boolean;
}

export const Navbar: FC<NavbarProps> = ({ bordered = true, left, right }) => {
  return (
    <nav
      className={clsx(
        "text-size-smaller",
        "header-nav",
        styles.header,
        bordered ? styles.bordered : undefined
      )}
      aria-label="breadcrumb"
      data-unsearchable={true}
    >
      <div className={clsx(styles.left)}>{left}</div>
      <div
        className={clsx(styles.right, right ? styles.hasChildren : undefined)}
      >
        {right}
      </div>
    </nav>
  );
};
