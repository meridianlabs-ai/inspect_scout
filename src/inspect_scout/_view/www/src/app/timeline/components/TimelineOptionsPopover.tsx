import { FC } from "react";

import { PopOver } from "../../../components/PopOver";
import type { UseTimelineConfigResult } from "../hooks/useTimelineConfig";
import type { MarkerKind } from "../utils/markers";

import styles from "./TimelineOptionsPopover.module.css";

// =============================================================================
// Types
// =============================================================================

interface TimelineOptionsPopoverProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  positionEl: HTMLElement | null;
  config: UseTimelineConfigResult;
}

// =============================================================================
// Constants
// =============================================================================

const kMarkerKindLabels: Array<{ kind: MarkerKind; label: string }> = [
  { kind: "error", label: "Errors" },
  { kind: "compaction", label: "Compaction" },
  { kind: "branch", label: "Branches" },
];

// =============================================================================
// Component
// =============================================================================

export const TimelineOptionsPopover: FC<TimelineOptionsPopoverProps> = ({
  isOpen,
  setIsOpen,
  positionEl,
  config,
}) => {
  return (
    <PopOver
      id="timeline-options-popover"
      positionEl={positionEl}
      isOpen={isOpen}
      setIsOpen={setIsOpen}
      placement="bottom-end"
      hoverDelay={-1}
    >
      <div className={`${styles.title} text-size-smaller`}>View Options</div>
      <div className={`${styles.rows} text-size-smaller`}>
        {kMarkerKindLabels.map(({ kind, label }) => {
          const checked = config.markerKinds.includes(kind);
          return (
            <div
              key={kind}
              className={styles.row}
              onClick={() => config.toggleMarkerKind(kind)}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={(e) => {
                  e.stopPropagation();
                  config.toggleMarkerKind(kind);
                }}
              />
              {label}
            </div>
          );
        })}
        <div
          className={styles.row}
          onClick={() => config.setIncludeUtility(!config.includeUtility)}
        >
          <input
            type="checkbox"
            checked={config.includeUtility}
            onChange={(e) => {
              e.stopPropagation();
              config.setIncludeUtility(!config.includeUtility);
            }}
          />
          Utility agents
        </div>
      </div>
    </PopOver>
  );
};
