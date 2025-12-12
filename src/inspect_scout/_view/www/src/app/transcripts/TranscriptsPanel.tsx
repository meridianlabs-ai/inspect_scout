import clsx from "clsx";
import { FC } from "react";
import { useNavigate } from "react-router-dom";

import { ApplicationIcons } from "../appearance/icons";
import { ActivityBar } from "../components/ActivityBar";

import styles from "./TranscriptsPanel.module.css";

export const TranscriptsPanel: FC = () => {
  const navigate = useNavigate();
  const activities = [
    {
      id: "transcripts",
      label: "Transcripts",
      icon: ApplicationIcons.transcript,
      description: "View and manage transcripts",
    },
    {
      id: "results",
      label: "Results",
      icon: ApplicationIcons.metrics,
      description: "View and manage scans",
    },
  ];

  return (
    <div className={clsx(styles.panel)}>
      <ActivityBar
        activities={activities}
        onSelectActivity={function (id: string): void {
          if (id === "transcripts") {
            // Already on transcripts panel
            return;
          }

          if (id === "results") {
            void navigate("/scans");
          }
        }}
        selectedActivity={"transcripts"}
      />
      <div className={clsx(styles.content)}>Transcripts go here</div>
    </div>
  );
};
