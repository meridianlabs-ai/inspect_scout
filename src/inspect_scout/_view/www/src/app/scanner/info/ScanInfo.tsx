import clsx from "clsx";
import { FC } from "react";

import { Card, CardBody, CardHeader } from "../../../components/Card";
import { MetaDataGrid } from "../../../content/MetaDataGrid";
import { RecordTree } from "../../../content/RecordTree";
import { useStore } from "../../../state/store";
import { Status } from "../../../types";
import { formatDateTime } from "../../../utils/format";

import styles from "./ScanInfo.module.css";

export const ScanInfo: FC = () => {
  const selectedStatus = useStore((state) => state.selectedScanStatus);
  if (!selectedStatus) {
    return null;
  }
  return (
    <>
      <ScanInfoCard
        className={clsx(styles.container)}
        selectedStatus={selectedStatus}
      />
      <ScanMetadataCard
        className={clsx(styles.container)}
        selectedStatus={selectedStatus}
      />
      <ScannerInfoCard
        className={clsx(styles.container)}
        selectedStatus={selectedStatus}
      />
      <TranscriptsInfoCard
        className={clsx(styles.container)}
        selectedStatus={selectedStatus}
      />
    </>
  );
};

interface ScanInfoCardProps {
  selectedStatus: Status;
  className?: string | string[];
}
const ScanInfoCard: FC<ScanInfoCardProps> = ({ selectedStatus, className }) => {
  return (
    <InfoCard
      title={`Scan: ${selectedStatus.spec.scan_name}`}
      className={clsx(className, "text-size-small")}
    >
      <MetaDataGrid
        key={`plan-md-task`}
        className={"text-size-small"}
        entries={{
          ID: selectedStatus.spec.scan_id,
          Name: selectedStatus.spec.scan_name,
          Args: selectedStatus.spec.scan_args,
          "Source File": selectedStatus.spec.scan_file,
          Origin: selectedStatus.spec.revision.origin,
          Commit: selectedStatus.spec.revision.commit,
          Packages: selectedStatus.spec.packages,
          Options: selectedStatus.spec.options,

          Timestamp: formatDateTime(new Date(selectedStatus.spec.timestamp)),
        }}
      />
    </InfoCard>
  );
};

interface ScanMetadataCardProps {
  selectedStatus: Status;
  className?: string | string[];
}
const ScanMetadataCard: FC<ScanMetadataCardProps> = ({
  selectedStatus,
  className,
}) => {
  if (Object.keys(selectedStatus.spec.metadata).length === 0) {
    return null;
  }

  return (
    <InfoCard title={"Metadata"} className={className}>
      <RecordTree id="scan-metadata" record={selectedStatus.spec.metadata} />
    </InfoCard>
  );
};

interface TranscriptsInfoCardProps {
  selectedStatus: Status;
  className?: string | string[];
}

const TranscriptsInfoCard: FC<TranscriptsInfoCardProps> = ({
  selectedStatus,
  className,
}) => {
  const fieldsDict = selectedStatus.spec.transcripts.fields.reduce(
    (acc, curr) => {
      acc[curr["name"]] = curr["type"];
      return acc;
    },
    {} as Record<string, string>
  );
  return (
    <InfoCard title={"Transcripts"} className={className}>
      <MetaDataGrid
        key={`plan-md-task`}
        className={"text-size-small"}
        entries={{
          Type: selectedStatus.spec.transcripts.type,
          Count: selectedStatus.spec.transcripts.count,
          Fields: fieldsDict,
        }}
      />
    </InfoCard>
  );
};

interface ScannerInfoCardProps {
  selectedStatus: Status;
  className?: string | string[];
}

const ScannerInfoCard: FC<ScannerInfoCardProps> = ({
  selectedStatus,
  className,
}) => {
  return (
    <InfoCard title={"Scanners"} className={className}>
      <MetaDataGrid
        key={`plan-md-task`}
        className={"text-size-small"}
        entries={{
          ...selectedStatus.spec.scanners,
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
