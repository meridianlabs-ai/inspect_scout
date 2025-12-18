import clsx from "clsx";
import { FC } from "react";

import { useStore } from "../../../state/store";
import { Status } from "../../../types";
import { Footer } from "../../components/Footer";

import { ScanResultsBody } from "./ScanResultsBody";
import { ScanResultsOutline } from "./ScanResultsOutline";
import styles from "./ScanResultsPanel.module.css";

export const ScanResultsPanel: FC<{ selectedStatus: Status }> = ({
  selectedStatus,
}) => {
  const visibleItemsCount = useStore(
    (state) => state.visibleScannerResultsCount
  );
  return (
    <div className={clsx(styles.container)}>
      <ScanResultsOutline selectedStatus={selectedStatus} />
      <ScanResultsBody selectedStatus={selectedStatus} />
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
