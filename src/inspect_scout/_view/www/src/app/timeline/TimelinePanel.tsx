import {
  VscodeOption,
  VscodeSingleSelect,
} from "@vscode-elements/react-elements";
import { FC, useState } from "react";

import { useDocumentTitle } from "../../hooks/useDocumentTitle";

import { timelineScenarios } from "./syntheticNodes";
import styles from "./TimelinePanel.module.css";

export const TimelinePanel: FC = () => {
  useDocumentTitle("Timeline");

  const [selectedIndex, setSelectedIndex] = useState(0);
  const scenario = timelineScenarios[selectedIndex];

  return (
    <div className={styles.container}>
      <div className={styles.headerRow}>
        <h2 className={styles.title}>Timeline</h2>
        <VscodeSingleSelect
          value={String(selectedIndex)}
          onChange={(e) => {
            const target = e.target as HTMLSelectElement;
            setSelectedIndex(Number(target.value));
          }}
          className={styles.scenarioSelect}
        >
          {timelineScenarios.map((s, i) => (
            <VscodeOption key={i} value={String(i)}>
              {s.name}
            </VscodeOption>
          ))}
        </VscodeSingleSelect>
        <span className={styles.scenarioDescription}>
          {scenario?.description}
        </span>
      </div>
      <div className={styles.content}>{/* Timeline prototype goes here */}</div>
    </div>
  );
};
