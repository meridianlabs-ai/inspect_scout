import clsx from "clsx";
import { FC } from "react";

import { PopOver } from "../../components/PopOver";

import { useTranscriptColumnFilter } from "./hooks/useTranscriptColumnFilter";
import styles from "./TranscriptFilterPopover.module.css";

export interface TranscriptFilterProps {
  showing: boolean;
  setShowing: (showing: boolean) => void;
  positionEl: HTMLElement | null;
}

export const TranscriptFilterPopover: FC<TranscriptFilterProps> = ({
  showing,
  positionEl,
  setShowing,
}) => {
  const {
    excludedEventTypes,
    isDefaultFilter,
    isDebugFilter,
    setDefaultFilter,
    setDebugFilter,
    toggleEventType,
    arrangedEventTypes,
  } = useTranscriptColumnFilter();

  return (
    <PopOver
      id={`transcript-filter-popover`}
      positionEl={positionEl}
      isOpen={showing}
      setIsOpen={setShowing}
      placement="bottom-end"
      hoverDelay={-1}
    >
      <div className={clsx(styles.links, "text-size-smaller")}>
        <a
          className={clsx(
            styles.link,
            isDefaultFilter ? styles.selected : undefined
          )}
          onClick={() => setDefaultFilter()}
        >
          Default
        </a>
        |
        <a
          className={clsx(
            styles.link,
            isDebugFilter ? styles.selected : undefined
          )}
          onClick={() => setDebugFilter()}
        >
          Debug
        </a>
      </div>

      <div className={clsx(styles.grid, "text-size-smaller")}>
        {arrangedEventTypes(2).map((eventType) => {
          const isExcluded = excludedEventTypes.includes(eventType);
          return (
            <div
              key={eventType}
              className={clsx(styles.row)}
              onClick={() => {
                toggleEventType(eventType, isExcluded);
              }}
            >
              <input
                type="checkbox"
                checked={!isExcluded}
                onChange={(e) => {
                  e.stopPropagation();
                  toggleEventType(eventType, isExcluded);
                }}
              />
              {eventType}
            </div>
          );
        })}
      </div>
    </PopOver>
  );
};
