import { FC } from "react"
import { Link } from "react-router-dom"
import { Scan } from "../../types";
import { scanRoute } from "../../router/url";
import { toRelativePath } from "../../utils/path";
import { useStore } from "../../state/store";

import styles from "./ScanRow.module.css";
import clsx from "clsx";

export interface ScanRowProps {
  scan: Scan;
}

export const ScanRow: FC<ScanRowProps> = ({scan}) => {

    const resultsDir = useStore((state) => state.resultsDir);
    
    const relativePath = resultsDir
      ? toRelativePath(scan.location, resultsDir)
      : scan.location;
    
    // TODO: Vscode doesn't support linking navigation
    return <div className={clsx(styles.scanRow)}>
        <Link
          key={scan.location}
          to={scanRoute(relativePath)}
          className="list-group-item list-group-item-action"
        >
          {scan.location || 'Unnamed Scan'}
        </Link>
      </div>
}