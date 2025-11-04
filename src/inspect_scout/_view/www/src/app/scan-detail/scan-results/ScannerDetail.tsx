import { FC } from "react";

import { IPCDataframe } from "../../../types";

interface ScannerDetailProps {
  scanner: IPCDataframe;
}

export const ScannerDetail: FC<ScannerDetailProps> = ({ scanner }) => {
  return <div>{scanner.format}</div>;
};
