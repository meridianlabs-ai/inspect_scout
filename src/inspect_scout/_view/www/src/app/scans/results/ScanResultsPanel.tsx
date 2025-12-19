import clsx from "clsx";
import { FC } from "react";

import { useStore } from "../../../state/store";
import { Status } from "../../../types";
import { Footer } from "../../components/Footer";
import { useSelectedScanner } from "../../hooks";

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
  const selectedScannerInfo = {
    name: selectedScanner,
    columnTable: useStore((state) => state.getSelectedScanResultData)(
      selectedScanner
    ),
    isLoading: !!useStore((state) => state.loadingData),
    error: useStore((state) => state.scopedErrors["dataframe"]),
  };

  return (
    <div className={clsx(styles.container)}>
      <ScanResultsOutline selectedScan={selectedScan} />
      <ScanResultsBody
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
