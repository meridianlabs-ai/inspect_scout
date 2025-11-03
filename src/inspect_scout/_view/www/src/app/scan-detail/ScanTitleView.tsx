import { FC } from "react";
import { useStore } from "../../state/store";

import styles from "./ScanTitleView.module.css";
import clsx from "clsx";

export const ScanTitleView: FC = () => {
    const selectedResults = useStore((state) => state.selectedResults);
    
    return <div className={clsx(styles.scanTitleView)}>
        <div className={clsx(styles.leftColumn)}>
            <h1>{selectedResults?.spec.scan_name}</h1>
            <h2>{selectedResults?.spec.scan_id}</h2>
            <h3 className={clsx(styles.subtitle, "text-style-secondary")}>{selectedResults?.spec.scan_file}</h3>
        </div>
        
        
        <div className={clsx(styles.rightColumn)}>
        <div className={"text-size-smaller"}>{selectedResults?.complete ? "Complete" : "Incomplete"}</div>
        </div>
    </div>;
}