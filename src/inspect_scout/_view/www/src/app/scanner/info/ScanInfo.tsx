import clsx from "clsx";
import { FC } from "react";

import { Card, CardBody, CardHeader } from "../../../components/Card";
import { MetaDataGrid } from "../../../content/MetaDataGrid";
import { RecordTree } from "../../../content/RecordTree";
import { Results } from "../../../types";
import { formatDateTime } from "../../../utils/format";
import { useSelectedResults } from "../../hooks";

import styles from "./ScanInfo.module.css";

export const ScanInfo: FC = () => {
  const selectedResults = useSelectedResults();
  if (!selectedResults) {
    return null;
  }
  return (
    <>
      <ScanInfoCard
        className={clsx(styles.container)}
        selectedResults={selectedResults}
      />
      <ScanMetadataCard
        className={clsx(styles.container)}
        selectedResults={selectedResults}
      />
      <ScannerInfoCard
        className={clsx(styles.container)}
        selectedResults={selectedResults}
      />
      <TranscriptsInfoCard
        className={clsx(styles.container)}
        selectedResults={selectedResults}
      />
    </>
  );
};

interface ScanInfoCardProps {
  selectedResults: Results;
  className?: string | string[];
}
const ScanInfoCard: FC<ScanInfoCardProps> = ({
  selectedResults,
  className,
}) => {
  return (
    <InfoCard
      title={`Scan: ${selectedResults.spec.scan_name}`}
      className={clsx(className, "text-size-small")}
    >
      <MetaDataGrid
        key={`plan-md-task`}
        className={"text-size-small"}
        entries={{
          ID: selectedResults.spec.scan_id,
          Name: selectedResults.spec.scan_name,
          Args: selectedResults.spec.scan_args,
          "Source File": selectedResults.spec.scan_file,
          Origin: selectedResults.spec.revision.origin,
          Commit: selectedResults.spec.revision.commit,
          Packages: selectedResults.spec.packages,
          Options: selectedResults.spec.options,

          Timestamp: formatDateTime(new Date(selectedResults.spec.timestamp)),
        }}
      />
    </InfoCard>
  );
};

interface ScanMetadataCardProps {
  selectedResults: Results;
  className?: string | string[];
}
const ScanMetadataCard: FC<ScanMetadataCardProps> = ({
  selectedResults,
  className,
}) => {
  if (Object.keys(selectedResults.spec.metadata).length === 0) {
    return null;
  }

  return (
    <InfoCard title={"Metadata"} className={className}>
      <RecordTree id="scan-metadata" record={selectedResults.spec.metadata} />
    </InfoCard>
  );
};

interface TranscriptsInfoCardProps {
  selectedResults: Results;
  className?: string | string[];
}

const TranscriptsInfoCard: FC<TranscriptsInfoCardProps> = ({
  selectedResults,
  className,
}) => {
  const fieldsDict = selectedResults.spec.transcripts.fields.reduce(
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
          Type: selectedResults.spec.transcripts.type,
          Count: selectedResults.spec.transcripts.count,
          Fields: fieldsDict,
        }}
      />
    </InfoCard>
  );
};

interface ScannerInfoCardProps {
  selectedResults: Results;
  className?: string | string[];
}

const ScannerInfoCard: FC<ScannerInfoCardProps> = ({
  selectedResults,
  className,
}) => {
  return (
    <InfoCard title={"Scanners"} className={className}>
      <MetaDataGrid
        key={`plan-md-task`}
        className={"text-size-small"}
        entries={{
          ...selectedResults.spec.scanners,
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
