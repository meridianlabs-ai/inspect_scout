import { FC, ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  activities,
  getActivityById,
  getActivityByRoute,
} from "../../router/activities";
import { AppConfig } from "../../types/api-types";

import { ActivityBar } from "./ActivityBar";
import styles from "./ActivityBarLayout.module.css";
import { ProjectBar } from "./ProjectBar";

interface ActivityBarLayoutProps {
  config: AppConfig;
  children: ReactNode;
}

/**
 * Layout component that wraps all routes with the ActivityBar navigation
 */
export const ActivityBarLayout: FC<ActivityBarLayoutProps> = ({
  config,
  children,
}) => {
  const location = useLocation();
  const navigate = useNavigate();

  // Determine the currently selected activity based on the current route
  const currentActivity = getActivityByRoute(location.pathname);
  const selectedActivityId = currentActivity?.id ?? "";

  const handleSelectActivity = (activityId: string) => {
    const activity = getActivityById(activityId);
    if (activity) {
      void navigate(activity.route);
    }
  };

  return (
    <div className={styles.outerLayout}>
      <ProjectBar config={config} />
      <div className={styles.layout}>
        <ActivityBar
          activities={activities.map((a) => ({
            id: a.id,
            label: a.label,
            icon: a.icon,
            description: a.description,
          }))}
          selectedActivity={selectedActivityId}
          onSelectActivity={handleSelectActivity}
        />
        <div className={styles.content}>{children}</div>
      </div>
    </div>
  );
};
