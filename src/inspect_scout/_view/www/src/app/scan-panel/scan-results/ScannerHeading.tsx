import clsx from "clsx";
import { FC } from "react";

import { Scanner } from "../../../types";

import styles from "./ScannerHeading.module.css";

interface ScannerHeadingProps {
  scanner: Scanner;
}

export const ScannerHeading: FC<ScannerHeadingProps> = ({ scanner }) => {
  return (
    <div className={clsx(styles.container)}>
      {scanner.name}({toArgs(scanner.params).join(", ")})
    </div>
  );
};

const toArgs = (params: Record<string, unknown>): string[] => {
  const args: string[] = [];
  for (const [key, value] of Object.entries(params)) {
    args.push(`${key}:${String(value)}`);
  }
  return args;
};
