import clsx from "clsx";
import { FC, ReactNode } from "react";

import styles from "./Navbar.module.css";
import { NavButton, NavButtons } from "./NavButtons";

interface NavbarProps {
  leftButtons?: NavButton[];
  left?: ReactNode;
  right?: ReactNode;
  rightButtons?: NavButton[];
  bordered?: boolean;
}

export const Navbar: FC<NavbarProps> = ({
  bordered = true,
  left,
  right,
  leftButtons,
  rightButtons,
}) => {
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
      <div className={clsx(leftButtons ? styles.leftButtons : undefined)}>
        {leftButtons && <NavButtons buttons={leftButtons} />}
      </div>
      <div className={clsx(leftButtons ? styles.left : undefined)}>{left}</div>
      <div
        className={clsx(styles.right, right ? styles.hasChildren : undefined)}
      >
        {right}
      </div>
      <div className={clsx(rightButtons ? styles.rightButtons : undefined)}>
        {rightButtons && <NavButtons buttons={rightButtons} />}
      </div>
    </nav>
  );
};
