import clsx from "clsx";
import { useStore } from "../../../state/store";
import { FC } from "react";

import styles from "./ScanResultsTOC.module.css";
import { Results } from "../../../types";

interface TOCEntry {
    icon?: string;
    title: string;
    count: number;
}

const toEntries = (results?: Results): TOCEntry[] => {
    if (!results) {
        return [];
    }
    const entries: TOCEntry[] = [];

    console.log(results)
    for (const scanner of Object.keys(results.summary.scanners)) {
        const summary = results.summary.scanners[scanner];
        entries.push({
            title: scanner,
            count: summary?.results || 0,
        });
    }
    return entries;
}


export const ScanResultsTOC: FC = () => {
    const results = useStore((state) => state.selectedResults);
    const entries = toEntries(results);

    return <div className={clsx(styles.container)}>
        {entries.map((entry) => {
            return <div key={entry.title} className={clsx(styles.entry)}>
                {entry.icon && <img src={entry.icon} className={clsx(styles.icon)}/>}
                <span className={clsx(styles.title)}>{entry.title}</span>
                <span className={clsx(styles.count)}>{entry.count}</span>
            </div>
        })}
    </div>
}   