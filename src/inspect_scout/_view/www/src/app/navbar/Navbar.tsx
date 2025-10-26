import clsx from "clsx";
import { FC, ReactNode } from "react";
import { Link } from "react-router-dom";
import styles from "./Navbar.module.css";
import { Icons } from "../theme/icons";
import { scansRoute } from "../../router/url";

interface NavbarProps {
  children?: ReactNode;
}

export const Navbar: FC<NavbarProps> = ({ children }) => {
  return (
    <nav
      className={clsx(styles.header)}
      aria-label="breadcrumb"
      data-unsearchable={true}
    >
      <div className={clsx(styles.left)}>
        <Link to={scansRoute()} className={clsx(styles.toolbarButton)}>
          <i className={clsx(Icons.back)} />
        </Link>
        <Link
          to={scansRoute()}
          className={clsx(styles.toolbarButton)}
        >
          <i className={clsx(Icons.home)} />
        </Link>
      </div>
      <div className={clsx(styles.right)}>{children}</div>
    </nav>
  );
};
