import clsx from "clsx";
import { FC } from "react";

import { ApplicationIcons } from "./icons";
import styles from "./NoContentsPanel.module.css";

interface NoContentsPanelProps {
  text: string;
  icon?: string;
}

export const NoContentsPanel: FC<NoContentsPanelProps> = ({ text, icon }) => {
  return (
    <div className={clsx(styles.panel)}>
      <div className={clsx(styles.container, "text-size-smaller")}>
        <i className={icon || ApplicationIcons.noSamples} />
        <div>{text}</div>
      </div>
    </div>
  );
};
