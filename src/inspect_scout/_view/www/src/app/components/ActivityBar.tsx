import clsx from "clsx";
import { FC, MouseEvent } from "react";

import styles from "./ActivityBar.module.css";

interface Activity {
  id: string;
  label: string;
  icon: string;
  description?: string;
}

interface ActivityBarProps {
  activities: Activity[];
  onSelectActivity: (id: string, e: MouseEvent<HTMLDivElement>) => void;
  selectedActivity: string;
}

export const ActivityBar: FC<ActivityBarProps> = ({
  activities,
  selectedActivity,
  onSelectActivity,
}) => {
  return (
    <div className={clsx(styles.activityBar)}>
      <div className={clsx(styles.activityHost)}>
        {activities.map((activity) => (
          <Activity
            key={activity.id}
            id={activity.id}
            label={activity.label}
            icon={activity.icon}
            description={activity.description}
            selected={activity.id === selectedActivity}
            onSelect={onSelectActivity}
          />
        ))}
      </div>
    </div>
  );
};

interface ActivityProps extends Activity {
  selected?: boolean;
  onSelect: (id: string, e: MouseEvent<HTMLDivElement>) => void;
}

const Activity: FC<ActivityProps> = ({
  id,
  label,
  icon,
  description,
  selected,
  onSelect,
}) => {
  return (
    <div
      id={id}
      className={clsx(styles.activity, selected ? styles.selected : undefined)}
      title={description}
      onClick={(e) => onSelect(id, e)}
    >
      <i className={clsx(styles.icon, icon)}></i>
      <div className={clsx(styles.label)}>{label}</div>
    </div>
  );
};
