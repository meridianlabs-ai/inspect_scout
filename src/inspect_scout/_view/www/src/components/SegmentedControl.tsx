import clsx from "clsx";
import { FC, useCallback } from "react";

import styles from "./SegmentedControl.module.css";

export interface Segment {
  id: string;
  label: string;
  icon?: string;
  selectedId?: string;
}

export interface SegmentedControlProps {
  id?: string;
  segments: Segment[];
  selectedId: string;
  onSegmentChange: (segmentId: string, index: number) => void;
}

export const SegmentedControl: FC<SegmentedControlProps> = ({
  id,
  segments,
  onSegmentChange,
  selectedId: selectedIdProp,
}) => {
  const handleSegmentClick = useCallback(
    (segmentId: string, index: number) => {
      onSegmentChange(segmentId, index);
    },
    [onSegmentChange]
  );

  const selectedId = selectedIdProp ?? segments[0]?.id ?? "";

  return (
    <div id={id} className={clsx(styles.rootControl)}>
      {segments.map((segment, index) => (
        <button
          key={segment.id}
          className={clsx(
            styles.segment,
            selectedId === segment.id && styles.selected,
            "text-size-smallest",
            selectedId === segment.id ? undefined : "text-style-secondary"
          )}
          onClick={() => handleSegmentClick(segment.id, index)}
          aria-pressed={selectedId === segment.id}
        >
          {segment.icon && <i className={segment.icon} />}
          <span>{segment.label}</span>
        </button>
      ))}
    </div>
  );
};
