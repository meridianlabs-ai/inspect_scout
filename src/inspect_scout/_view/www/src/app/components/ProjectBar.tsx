import { FC } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { getActivityByRoute } from "../../router/activities";
import { AppConfig } from "../../types/api-types";
import { ApplicationIcons } from "../../components/icons";

import styles from "./ProjectBar.module.css";
import { appAliasedPath } from "../server/useConfig";
import { clsx } from "clsx";

interface ProjectBarProps {
  config: AppConfig;
}

export const ProjectBar: FC<ProjectBarProps> = ({ config }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const currentActivity = getActivityByRoute(location.pathname);

  return (
    <div className={styles.projectBar}>
      <div className={styles.row}>
        <div className={styles.left}>
          <button
            type="button"
            className={clsx(styles.navButton, styles.historyButton)}
            onClick={() => navigate(-1)}
            aria-label="Back"
            title="Back"
          >
            <i className={ApplicationIcons.navbar.back} />
          </button>
          <button
            type="button"
            className={clsx(styles.navButton, styles.historyButton)}
            onClick={() => navigate(1)}
            aria-label="Forward"
            title="Forward"
          >
            <i className={ApplicationIcons.navbar.forward} />
          </button>
          <button
            type="button"
            className={styles.navButton}
            onClick={() => {
              if (currentActivity) {
                void navigate(currentActivity.route);
              }
            }}
            aria-label="Home"
            title="Home"
          >
            <i className={ApplicationIcons.navbar.home} />
          </button>
        </div>
        <span className={styles.center}>
          {appAliasedPath(config, config.project_dir)}
        </span>
        <div className={styles.right}>
          <button type="button" className={styles.navButton}>
            <i className={ApplicationIcons.config} />
            &nbsp;Project
          </button>
        </div>
      </div>
    </div>
  );
};
