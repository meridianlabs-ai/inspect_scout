import { clsx } from "clsx";
import { FC } from "react";

import { ActivityBar } from "../../components/ActivityBar";
import { useStore } from "../../state/store";
import { Navbar } from "../navbar/Navbar";

import styles from "./ScanResultPanel.module.css";

export const ScanResultPanel: FC = () => {
  const singleFileMode = useStore((state) => state.singleFileMode);
  const loading = useStore((state) => state.loading);
  return (
    <div className={clsx(styles.root)}>
      {singleFileMode || <Navbar />}
      <ActivityBar animating={!!loading} />
    </div>
  );
};
