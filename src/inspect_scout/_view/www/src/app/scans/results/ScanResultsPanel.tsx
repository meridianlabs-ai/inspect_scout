import { ColumnTable } from "arquero";
import clsx from "clsx";
import { FC } from "react";

import { useStore } from "../../../state/store";
import { Status } from "../../../types";
import { AsyncData } from "../../../utils/asyncData";
import { Footer } from "../../components/Footer";

import { ScanResultsBody } from "./ScanResultsBody";
import { ScanResultsOutline } from "./ScanResultsOutline";
import styles from "./ScanResultsPanel.module.css";

interface ScanResultsPanelProps {
  scanStatus: Status;
  dataframe: AsyncData<ColumnTable>;
}

export const ScanResultsPanel: FC<ScanResultsPanelProps> = ({ scanStatus, dataframe }) => {
  const visibleItemsCount = useStore(
    (state) => state.visibleScannerResultsCount
  );
  return (
    <div className={clsx(styles.container)}>
      <ScanResultsOutline scanStatus={scanStatus} />
      <ScanResultsBody scanStatus={scanStatus} dataframe={dataframe} />
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
