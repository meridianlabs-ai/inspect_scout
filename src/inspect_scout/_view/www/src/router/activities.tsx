import { ReactElement } from "react";

import { ScanJobsPanel } from "../app/scanJobs/ScanJobsPanel";
import { TranscriptsPanel } from "../app/transcripts/TranscriptsPanel";
import { ApplicationIcons } from "../components/icons";

export interface ActivityConfig {
  id: string;
  label: string;
  icon: string;
  route: string;
  routePatterns?: string[];
  description?: string;
  element: ReactElement;
}

export const activities: ActivityConfig[] = [
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
    element: <ScanJobsPanel />,
  },
];

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
