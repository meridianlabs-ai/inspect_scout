import clsx from "clsx";
import { FC } from "react";
import { Link } from "react-router-dom";

import styles from "./NavButtons.module.css";

export interface NavButton {
  // The title of the navigation button
  title: string;

  // The icon class for the navigation button
  icon: string;

  // The route URL for the navigation button
  route: string;
}

interface NavButtonsProps {
  buttons: NavButton[];
}

export const NavButtons: FC<NavButtonsProps> = ({ buttons }) => {
  return (
    <>
      {buttons.map((button, index) => (
        <Link
          key={index}
          to={button.route}
          className={clsx(styles.toolbarButton)}
          title={button.title}
          aria-label={button.title}
        >
          <i className={clsx(button.icon)} />
        </Link>
      ))}
    </>
  );
};
