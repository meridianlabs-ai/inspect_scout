import clsx from "clsx";
import { FC } from "react";

import { useStore } from "../../../state/store";
import { Footer } from "../../components/Footer";

import { ScanResultsBody } from "./ScanResultsBody";
import { ScanResultsOutline } from "./ScanResultsOutline";
import styles from "./ScanResultsPanel.module.css";

export const ScanResultsPanel: FC = () => {
  const visibleItemsCount = useStore(
    (state) => state.visibleScannerResultsCount
  );
  return (
    <div className={clsx(styles.container)}>
      <ScanResultsOutline />
      <ScanResultsBody />
      <Footer
        id={""}
        className={styles.footer}
        itemCount={visibleItemsCount}
        paginated={false}
        labels={{
          singular: "result",
          plural: "results",
        }}
      />
    </div>
  );
};
