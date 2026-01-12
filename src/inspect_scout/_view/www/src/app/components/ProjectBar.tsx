import { FC } from "react";

import { AppConfig } from "../../types/api-types";

import styles from "./ProjectBar.module.css";
import { appAliasedPath } from "../server/useConfig";

interface ProjectBarProps {
  config: AppConfig;
}

export const ProjectBar: FC<ProjectBarProps> = ({ config }) => {
  return (
    <div className={styles.projectBar}>
      <div className={styles.row}>
        <span className={styles.left}>
          {appAliasedPath(config, config.project_dir)}
        </span>
        <span className={styles.right}>{config.project.transcripts ?? ""}</span>
      </div>
      <div className={styles.row}>
        <span>{config.project.model ?? ""}</span>
      </div>
    </div>
  );
};
