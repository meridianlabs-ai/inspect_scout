import { FC } from "react"

import styles from "./ScanResults.module.css"
import clsx from "clsx"
import { ScanResultsTOC } from "./ScanResultsTOC";

export const ScanResults: FC = () => {
    


    


    return <div className={clsx(styles.container)}>
        <ScanResultsTOC/>
        <div>Body</div>
    </div>
}