import clsx from "clsx";
import { FC } from "react";

import { useStore } from "../../../state/store";
import { Footer } from "../../components/Footer";

import { ScanResultsBody } from "./ScanResultsBody";
import { ScanResultsOutline } from "./ScanResultsOutline";
import styles from "./ScanResultsPanel.module.css";

export const ScanResultsPanel: FC = () => {
  const visibleCount =
    useStore((state) => state.visibleScannerResultCount) || 0;
  return (
    <div className={clsx(styles.container)}>
      <ScanResultsOutline />
      <ScanResultsBody />
      <Footer
        id={""}
        className={styles.footer}
        itemCount={visibleCount}
        paginated={false}
        labels={{
          singular: "result",
          plural: "results",
        }}
      />
    </div>
  );
};
