import { FC } from "react";

import { AppConfig } from "../../types/api-types";
import { ApplicationIcons } from "../../components/icons";

import styles from "./ProjectBar.module.css";
import { appAliasedPath } from "../server/useConfig";
import { ToolButton } from "./ToolButton";

interface ProjectBarProps {
  config: AppConfig;
}

export const ProjectBar: FC<ProjectBarProps> = ({ config }) => {
  return (
    <div className={styles.projectBar}>
      <div className={styles.row}>
        <span className={styles.center}>
          {appAliasedPath(config, config.project_dir)}
        </span>
        <div className={styles.right}>
          <ToolButton
            label="Project"
            icon={ApplicationIcons.config}
            className={styles.projectButton}
          />
        </div>
      </div>
    </div>
  );
};
