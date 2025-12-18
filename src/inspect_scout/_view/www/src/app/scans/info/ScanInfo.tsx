import clsx from "clsx";
import { FC } from "react";

import { Card, CardBody, CardHeader } from "../../../components/Card";
import { MetaDataGrid } from "../../../content/MetaDataGrid";
import { RecordTree } from "../../../content/RecordTree";
import { Status } from "../../../types";

import styles from "./ScanInfo.module.css";

export const ScanInfo: FC<{ selectedScan: Status }> = ({ selectedScan }) => {
  return (
    <>
      <ScanInfoCard
        className={clsx(styles.container)}
        selectedScan={selectedScan}
      />
      <ScanMetadataCard
        className={clsx(styles.container)}
        selectedScan={selectedScan}
      />
      <ScannerInfoCard
        className={clsx(styles.container)}
        selectedScan={selectedScan}
      />
    </>
  );
};

interface ScanInfoCardProps {
  selectedScan: Status;
  className?: string | string[];
}
const ScanInfoCard: FC<ScanInfoCardProps> = ({ selectedScan, className }) => {
  const record = {
    ID: selectedScan.spec.scan_id,
    Name: selectedScan.spec.scan_name,
  };
  if (selectedScan.spec.scan_args) {
    record["Args"] = selectedScan.spec.scan_args;
  }
  if (selectedScan.spec.scan_file) {
    record["Source File"] = selectedScan.spec.scan_file;
  }
  if (selectedScan.spec.revision?.origin) {
    record["Origin"] = selectedScan.spec.revision?.origin;
  }
  if (selectedScan.spec.revision?.commit) {
    record["Commit"] = selectedScan.spec.revision?.commit;
  }
  if (selectedScan.spec.packages) {
    record["Packages"] = selectedScan.spec.packages;
  }
  if (selectedScan.spec.options) {
    record["Options"] = selectedScan.spec.options;
  }

  return (
    <InfoCard
      title={`Scan: ${selectedScan.spec.scan_name}`}
      className={clsx(className, "text-size-small")}
    >
      <MetaDataGrid
        key={`plan-md-task`}
        className={"text-size-small"}
        entries={record}
      />
    </InfoCard>
  );
};

interface ScanMetadataCardProps {
  selectedScan: Status;
  className?: string | string[];
}
const ScanMetadataCard: FC<ScanMetadataCardProps> = ({
  selectedScan,
  className,
}) => {
  if (
    !selectedScan.spec.metadata ||
    Object.keys(selectedScan.spec.metadata).length === 0
  ) {
    return null;
  }

  return (
    <InfoCard title={"Metadata"} className={className}>
      <RecordTree id="scan-metadata" record={selectedScan.spec.metadata} />
    </InfoCard>
  );
};

interface ScannerInfoCardProps {
  selectedScan: Status;
  className?: string | string[];
}

const ScannerInfoCard: FC<ScannerInfoCardProps> = ({
  selectedScan,
  className,
}) => {
  return (
    <InfoCard title={"Scanners"} className={className}>
      <MetaDataGrid
        key={`plan-md-task`}
        className={"text-size-small"}
        entries={{
          ...selectedScan.spec.scanners,
        }}
      />
    </InfoCard>
  );
};

interface InfoCardProps {
  title: string;
  className?: string | string[];
  children?: React.ReactNode;
}

const InfoCard: FC<InfoCardProps> = ({ title, className, children }) => {
  return (
    <Card className={className}>
      <CardHeader label={title} type="modern" />
      <CardBody>{children}</CardBody>
    </Card>
  );
};
