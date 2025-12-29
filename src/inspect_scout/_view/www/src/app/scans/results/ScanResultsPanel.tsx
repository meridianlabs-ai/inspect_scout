import clsx from "clsx";
import { FC } from "react";

import { useStore } from "../../../state/store";
import { Status } from "../../../types";
import { Footer } from "../../components/Footer";
import { useSelectedScanDataframe, useSelectedScanner } from "../../hooks";

import { ScanResultsBody } from "./ScanResultsBody";
import { ScanResultsOutline } from "./ScanResultsOutline";
import styles from "./ScanResultsPanel.module.css";

export const ScanResultsPanel: FC<{ selectedScan: Status }> = ({
  selectedScan,
}) => {
  const visibleItemsCount = useStore(
    (state) => state.visibleScannerResultsCount
  );
  const selectedScanner = useSelectedScanner();

  const {
    data: columnTable,
    loading: isLoading,
    error,
  } = useSelectedScanDataframe();
  const selectedScannerInfo = {
    columnTable,
    isLoading,
    error: error?.message,
  };

  return (
    <div className={clsx(styles.container)}>
      <ScanResultsOutline selectedScan={selectedScan} />
      <ScanResultsBody
        // TODO: This is slightly bogus. It really needs to be a scannerid since
        // nothing prevents two scanners from having the same name.
        scannerId={selectedScanner.data ?? "unknown"}
        selectedScan={selectedScan}
        selectedScanner={selectedScannerInfo}
      />
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
