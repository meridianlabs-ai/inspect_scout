import clsx from "clsx";
import { FC } from "react";

import { ScannerData } from "../types";
import { Explanation } from "../values/Explanation";
import { Identifier } from "../values/Identifier";
import { Value } from "../values/Value";

import styles from "./ScanResultHeader.module.css";

interface ScanResultHeaderProps {
  result?: ScannerData;
}

export const ScanResultHeader: FC<ScanResultHeaderProps> = ({ result }) => {
  return (
    <div className={clsx(styles.header, "text-size-smaller")}>
      <div className={clsx("text-style-label", "text-size-smallest")}>Id</div>
      <div className={clsx("text-style-label", "text-size-smallest")}>
        Explanation
      </div>
      <div className={clsx("text-style-label", "text-size-smallest")}>
        Value
      </div>
      <div>{result && <Identifier result={result} />}</div>
      <div>{result && <Explanation result={result} />}</div>
      <div>{result && <Value result={result} />}</div>
    </div>
  );
};
