import clsx from "clsx";
import { FC } from "react";

import styles from "./LoadingBar.module.css";

interface LoadingBarProps {
  loading: boolean;
}

export const LoadingBar: FC<LoadingBarProps> = ({ loading }) => {
  return (
    <div className={clsx(styles.wrapper)}>
      <div
        className={clsx(styles.container)}
        role="progressbar"
        aria-label="Progress bar"
        aria-valuenow={25}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        {loading && <div className={styles.animate} />}
      </div>
    </div>
  );
};
