import { FC } from "react";
import { MetaDataGrid } from "../../../content/MetaDataGrid";
import { useStore } from "../../../state/store";
import clsx from "clsx";

import styles from "./ScanInfo.module.css";
import { Card, CardBody, CardHeader } from "../../../components/Card";

export const ScanInfo: FC = () => {
  const selectedResults = useStore((state) => state.selectedResults);

  if (!selectedResults) {
    return null;
  }
  return (
    <Card className={clsx(styles.container)}>
      <CardHeader label="Scan Information" />
      <CardBody>
        <MetaDataGrid
          entries={
            (selectedResults?.spec || {}) as unknown as Record<string, unknown>
          }
        />
      </CardBody>
    </Card>
  );
};
