import { ReactElement } from "react";

import { RunScanPanel } from "../app/runScan/RunScanPanel";
import { ScansPanel } from "../app/scans/ScansPanel";
import { TranscriptsPanel } from "../app/transcripts/TranscriptsPanel";
import { ValidationPanel } from "../app/validation/ValidationPanel";
import { ApplicationIcons } from "../components/icons";

declare const __SCOUT_RUN_SCAN__: boolean;

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
    id: "project",
    label: "Project",
    icon: ApplicationIcons.config,
    route: "/project",
    routePatterns: ["/project"],
    description: "Project settings",
    element: <></>,
  },
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
    id: "runScan",
    label: "Run Scan",
    icon: ApplicationIcons.play,
    route: "/run",
    description: "Run scans and view active scans",
    element: <RunScanPanel />,
  },
  {
    id: "validation",
    label: "Validation",
    icon: ApplicationIcons.validation,
    route: "/validation",
    routePatterns: ["/validation"],
    description: "Manage validation sets",
    element: <ValidationPanel />,
  },
];

export const activities = allActivities.filter(
  (a) => a.id !== "runScan" || __SCOUT_RUN_SCAN__
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
