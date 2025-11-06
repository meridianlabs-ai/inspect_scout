import { FC } from "react";

import { MetaDataGrid } from "../../../content/MetaDataGrid";
import { ScannerData } from "../../scan/results/list/types";

interface InfoPanelProps {
  scannerData: ScannerData;
}

export const InfoPanel: FC<InfoPanelProps> = ({ scannerData }) => {
  return <MetaDataGrid entries={scannerData.metadata} />;
};
