import clsx from "clsx";
import { FC } from "react";

import { AppConfig } from "../../types/api-types";
import { appAliasedPath } from "../server/useConfig";

import styles from "./ProjectPanel.module.css";
// import { useProjectConfig } from "../server/useProjectConfig";

interface ProjectPanelProps {
  config: AppConfig;
}

export const ProjectPanel: FC<ProjectPanelProps> = ({ config }) => {
  // const { loading, error, data } = useProjectConfig();

  return (
    <div className={clsx(styles.container)}>
      <div className={styles.header}>Project</div>
      <div className={styles.detail}>
        {appAliasedPath(config, config.project_dir)}
      </div>
    </div>
  );
};
