import {
  VscodeButton,
  VscodeLabel,
  VscodeOption,
  VscodeSingleSelect,
} from "@vscode-elements/react-elements";
import { FC, useState } from "react";

import { ApplicationIcons } from "../../components/icons";
import { ScansNavbar } from "../components/ScansNavbar";
import { TranscriptsNavbar } from "../components/TranscriptsNavbar";
import { useFilterBarProps } from "../hooks/useFilterBarProps";
import { useScanners } from "../server/useScanners";
import { useStartScan } from "../server/useStartScan";
import { TranscriptFilterBar } from "../transcripts/TranscriptFilterBar";
import { useScansDir } from "../utils/useScansDir";
import { useTranscriptsDir } from "../utils/useTranscriptsDir";

import { LlmScannerParams, LlmScannerParamsValue } from "./LlmScannerParams";
import styles from "./RunScanPanel.module.css";
import { ScannerParamsPlaceholder } from "./ScannerParamsPlaceholder";

function getSelectValue(e: Event): string {
  return (e.target as HTMLSelectElement).value;
}

interface Props {
  onScanStarted: (scanId: string) => void;
}

const defaultLlmParams: LlmScannerParamsValue = {
  question: "",
  answerType: "boolean",
  excludeSystem: true,
  excludeReasoning: false,
  excludeToolUsage: false,
};

export const DefineScannerSection: FC<Props> = ({ onScanStarted }) => {
  const [selectedScanner, setSelectedScanner] = useState<string | null>(null);
  const [llmParams, setLlmParams] = useState(defaultLlmParams);
  const { loading, data: scanners } = useScanners();
  const mutation = useStartScan();

  const { displayTranscriptsDir, resolvedTranscriptsDir, setTranscriptsDir } =
    useTranscriptsDir(true);
  const { displayScansDir, setScansDir } = useScansDir(true);

  const { filterCodeValues, filterSuggestions, onFilterColumnChange } =
    useFilterBarProps(resolvedTranscriptsDir);

  const effectiveScanner = selectedScanner ?? scanners?.[0]?.name;
  const selectedScannerInfo = scanners?.find(
    (s) => s.name === effectiveScanner
  );
  const canRunScan =
    effectiveScanner === "inspect_scout/llm_scanner" &&
    llmParams.question.trim().length > 0 &&
    !mutation.isPending;

  const handleRunScan = () => {
    mutation.mutate(
      {
        name: "inspect_scout/llm_scanner",
        filter: [],
        limit: 100,
        scanners: [
          {
            name: "inspect_scout/llm_scanner",
            version: 0,
            params: {
              question: llmParams.question,
              answer: llmParams.answerType,
              preprocessor: {
                exclude_system: llmParams.excludeSystem,
                exclude_reasoning: llmParams.excludeReasoning,
                exclude_tool_usage: llmParams.excludeToolUsage,
              },
            },
          },
        ],
      },
      { onSuccess: (data) => onScanStarted(data.spec.scan_id) }
    );
  };

  return (
    <>
      <TranscriptsNavbar
        transcriptsDir={displayTranscriptsDir}
        setTranscriptsDir={setTranscriptsDir}
      />
      <TranscriptFilterBar
        filterCodeValues={filterCodeValues}
        filterSuggestions={filterSuggestions}
        onFilterColumnChange={onFilterColumnChange}
        includeColumnPicker={false}
      />
      <ScansNavbar scansDir={displayScansDir} setScansDir={setScansDir} />

      <div className={styles.defineScannerSection}>
        <h2 className={styles.sectionTitle}>Define Scanner</h2>

        {/* Scanner Selection */}
        <div className={styles.formGroup}>
          <VscodeLabel>Type</VscodeLabel>
          <div className={styles.scannerRow}>
            <VscodeSingleSelect
              value={effectiveScanner ?? ""}
              onChange={(e) => setSelectedScanner(getSelectValue(e))}
              disabled={loading}
            >
              {scanners?.map((s) => (
                <VscodeOption key={s.name} value={s.name}>
                  {s.name}
                </VscodeOption>
              ))}
            </VscodeSingleSelect>
            {selectedScannerInfo?.description && (
              <div className={styles.scannerDescription}>
                {selectedScannerInfo.description}
              </div>
            )}
          </div>
        </div>

        {/* Scanner Params */}
        {effectiveScanner === "inspect_scout/llm_scanner" ? (
          <LlmScannerParams value={llmParams} onChange={setLlmParams} />
        ) : effectiveScanner ? (
          <ScannerParamsPlaceholder scannerName={effectiveScanner} />
        ) : null}

        {/* Run Button */}
        <div className={styles.runScanRow}>
          <VscodeButton disabled={!canRunScan} onClick={handleRunScan}>
            <i className={ApplicationIcons.play} />
            Run Scan
          </VscodeButton>
          <div className={styles.mutationStatus}>
            start scan status: {mutation.status}
          </div>
        </div>
      </div>
    </>
  );
};
