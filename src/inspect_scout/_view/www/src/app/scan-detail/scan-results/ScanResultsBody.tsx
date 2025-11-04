import { FC } from "react";

import styles from "./ScanResultsBody.module.css";
import clsx from "clsx";
import { useSelectedScanner } from "./hooks";

export const ScanResultsBody: FC = () => {
  const selectedScanner = useSelectedScanner();

  return <div className={clsx(styles.body)}>{selectedScanner}</div>;
};
