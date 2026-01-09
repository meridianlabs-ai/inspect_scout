import { ReactElement } from "react";

import { ActivePanel } from "../app/active/ActivePanel";
import { ScansPanel } from "../app/scans/ScansPanel";
import { TranscriptsPanel } from "../app/transcripts/TranscriptsPanel";
import { ApplicationIcons } from "../components/icons";

declare const __SCOUT_ACTIVE__: boolean;

export interface ActivityConfig {
  id: string;
  label: string;
  icon: string;
  route: string;
  routePatterns?: string[];
  description?: string;
  element: ReactElement;
}

const allActivities: ActivityConfig[] = [
  {
    id: "transcripts",
    label: "Transcripts",
    icon: ApplicationIcons.transcript,
    route: "/transcripts",
    description: "View transcripts",
    element: <TranscriptsPanel />,
  },
  {
    id: "scans",
    label: "Scans",
    icon: ApplicationIcons.scanner,
    route: "/scans",
    routePatterns: ["/scans", "/scan"],
    description: "View results",
    element: <ScansPanel />,
  },
  {
    id: "active",
    label: "Active",
    icon: ApplicationIcons.running,
    route: "/active",
    description: "View active scans",
    element: <ActivePanel />,
  },
];

export const activities = allActivities.filter(
  (a) => a.id !== "active" || __SCOUT_ACTIVE__
);

export const getActivityByRoute = (
  path: string
): ActivityConfig | undefined => {
  // Match against routePatterns if defined, otherwise fall back to the primary route
  return activities.find((activity) => {
    const patterns = activity.routePatterns || [activity.route];
    return patterns.some((pattern) => path.startsWith(pattern));
  });
};

export const getActivityById = (id: string): ActivityConfig | undefined => {
  return activities.find((activity) => activity.id === id);
};
