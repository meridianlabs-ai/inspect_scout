import { clsx } from "clsx";
import { FC } from "react";
import { useLocation } from "react-router-dom";

import { ApplicationIcons } from "../../components/icons";
import { useLoggingNavigate } from "../../debugging/navigationDebugging";
import { getActivityByRoute } from "../../router/activities";
import { AppConfig } from "../../types/api-types";
import { appAliasedPath } from "../server/useAppConfig";

import styles from "./ProjectBar.module.css";

interface ProjectBarProps {
  config: AppConfig;
}

export const ProjectBar: FC<ProjectBarProps> = ({ config }) => {
  const navigate = useLoggingNavigate("ProjectBar");
  const location = useLocation();
  const currentActivity = getActivityByRoute(location.pathname);

  return (
    <div className={styles.projectBar}>
      <div className={styles.row}>
        <div className={styles.left}>
          <button
            type="button"
            className={clsx(styles.navButton, styles.historyButton)}
            onClick={() => void navigate(-1)}
            aria-label="Back"
            title="Back"
          >
            <i className={ApplicationIcons.navbar.back} />
          </button>
          <button
            type="button"
            className={clsx(styles.navButton, styles.historyButton)}
            onClick={() => void navigate(1)}
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
        <div className={styles.right}></div>
      </div>
    </div>
  );
};
